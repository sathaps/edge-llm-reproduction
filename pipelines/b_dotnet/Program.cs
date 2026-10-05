using System.Diagnostics;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using LangChain.Databases;
using LangChain.Databases.Sqlite;
using LangChain.DocumentLoaders;
using LangChain.Providers;
using LangChain.Providers.Ollama;

// Implementation B: a C# port of LangChain with its SQLite vector store.
// usage: dotnet run --project pipelines/b_dotnet -- --pdf MANUAL.pdf --model llama3:latest --out results/<run-id>
// Settings come from config/pipelines.json (section "b"); --set path=value overrides one key.

var opt = Options.Parse(args);
var cfg = Config.Load(opt.ConfigPath, "b", opt.Overrides);
Directory.CreateDirectory(opt.Out);

var baseUrl = opt.Ollama.TrimEnd('/');
using var http = new HttpClient { BaseAddress = new Uri(baseUrl + "/"), Timeout = TimeSpan.FromHours(1) };
using var provider = new OllamaProvider(baseUrl + "/api");
var embedder = new OllamaEmbeddingModel(provider, cfg.Str("embedding_model"));
var embedEndpoint = cfg["embedding_endpoint"]?.GetValue<string>() ?? "embed";

var docs = await new PdfPigPdfLoader().LoadAsync(DataSource.FromPath(opt.Pdf), new DocumentLoaderSettings { ShouldCollectMetadata = true });
var pageTexts = docs.Select(d => d.PageContent).ToList();
var chunks = Chunker.Build(cfg, pageTexts);
File.WriteAllLines(Path.Combine(opt.Out, "chunks.jsonl"),
    chunks.Select(c => JsonSerializer.Serialize(new { chunk_id = c.Id, pages = c.Pages, text = c.Text })));

var indexPath = Path.Combine(opt.Out, "index.db");
if (File.Exists(indexPath)) File.Delete(indexPath);
using var db = new SqLiteVectorDatabase(indexPath);
var dims = cfg["vector_store"]!["collection_dimensions"]!.GetValue<int>();
var collection = await db.GetOrCreateCollectionAsync("manual", dims);

var clock = Stopwatch.StartNew();
for (var i = 0; i < chunks.Count; i += 16)
{
    var batch = chunks.Skip(i).Take(16).ToList();
    var emb = await Embed(batch.Select(c => c.Text).ToArray());
    await collection.AddAsync(batch.Select((c, j) => new Vector
    {
        Id = c.Id, Text = c.Text, Embedding = emb[j],
        Metadata = new Dictionary<string, object> { ["chunk_id"] = c.Id },
    }).ToList());
}
var indexSeconds = clock.Elapsed.TotalSeconds;

var chat = opt.RetrievalOnly ? null : new OllamaChatModel(provider, opt.Model);
var questions = Questions.Read(opt);
var history = new List<Message>();
var retRows = new List<object>();
var ansRows = new List<object>();
var promptRows = new List<object>();
var topK = cfg["retrieval"]!["top_k"]!.GetValue<int>();
var maxDistance = cfg["retrieval"]!["max_distance"]?.GetValue<float>();
// "retrieve" is the pipeline. "none" sends an empty context. "oracle" sends the full text of the question's source pages.
var mode = cfg["retrieval"]!["mode"]?.GetValue<string>() ?? "retrieve";
var rewriting = cfg["query_rewriting"];

foreach (var q in questions)
{
    if (opt.Conversation == "fresh") history.Clear();
    var turn = history.Count(m => m.Role == MessageRole.Human) + 1;
    var query = q.Text;
    if (rewriting is not null && !opt.RetrievalOnly && turn >= rewriting["from_turn"]!.GetValue<int>())
        query = await Rewrite(chat!, cfg, q.Text, history);

    var qv = (await Embed(new[] { query }))[0];
    // The store ignores VectorSearchSettings.ScoreThreshold, so a threshold is applied here on the distance.
    var found = await collection.SearchAsync(VectorSearchRequest.ToVectorSearchRequest(qv),
        new VectorSearchSettings { NumberOfResults = topK });
    var hits = found.Items.Where(v => maxDistance is null || v.Distance <= maxDistance)
        .Select(v => (chunk: chunks.First(c => c.Id == (string)v.Metadata["chunk_id"]), v)).ToList();
    var given = mode == "oracle" ? Pages.Parse(q.SourcePages).Where(n => n >= 1 && n <= pageTexts.Count).ToList() : new List<int>();
    if (mode != "retrieve") hits.Clear();
    retRows.Add(new
    {
        question_id = q.Id, query_used = query, mode,
        given_text = mode == "oracle" ? string.Join("\n\n", given.Select(n => pageTexts[n - 1])) : null,
        retrieved = mode == "retrieve"
            ? hits.Select(h => new { chunk_id = h.chunk.Id, pages = h.chunk.Pages, score = (float?)null, distance = (float?)h.v.Distance }).ToList()
            : given.Select(n => new { chunk_id = $"page-{n}", pages = new List<int> { n }, score = (float?)null, distance = (float?)null }).ToList(),
    });
    if (opt.RetrievalOnly) continue;

    var context = mode == "oracle" ? string.Join("\n\n", given.Select(n => pageTexts[n - 1]))
        : string.Join("\n\n", hits.Select(h => h.chunk.Text));
    var template = cfg["grounding"]!["template"]!.GetValue<string>();
    var shortest = cfg["generation"]!["shortest_answer"]!.GetValue<bool>() ? cfg["grounding"]!["shortest_line"]!.GetValue<string>() : "";
    var prompt = template.Replace("{shortest_line}", shortest).Replace("{context}", context).Replace("{question}", q.Text);
    var wall = Stopwatch.StartNew();
    var response = await Generate(chat!, cfg, new[] { Message.Human(prompt) });
    wall.Stop();
    var answer = response.LastMessageContent ?? "";
    history.Add(Message.Human(prompt));
    history.Add(Message.Ai(answer));
    var ctx = await ContextLength(http, opt.Model);
    promptRows.Add(new { question_id = q.Id, messages = new[] { new { role = "user", content = prompt } } });
    ansRows.Add(new
    {
        question_id = q.Id, answer, wall_s = wall.Elapsed.TotalSeconds,
        prompt_eval_count = response.Usage.InputTokens, eval_count = response.Usage.OutputTokens,
        done_reason = response.FinishReason?.ToString(), context_length = ctx,
    });
}

File.WriteAllLines(Path.Combine(opt.Out, "retrieval.jsonl"), retRows.Select(r => JsonSerializer.Serialize(r)));
if (!opt.RetrievalOnly)
{
    File.WriteAllLines(Path.Combine(opt.Out, "answers.jsonl"), ansRows.Select(r => JsonSerializer.Serialize(r)));
    File.WriteAllLines(Path.Combine(opt.Out, "prompts.jsonl"), promptRows.Select(r => JsonSerializer.Serialize(r)));
}
File.WriteAllText(Path.Combine(opt.Out, "run.json"), JsonSerializer.Serialize(new
{
    implementation = "b", settings = JsonNode.Parse(cfg.ToJsonString()), model = opt.Model,
    model_digest = opt.RetrievalOnly ? null : await Digest(http, opt.Model),
    embedding_digest = await Digest(http, cfg.Str("embedding_model")),
    ollama_version = (await http.GetFromJsonAsync<JsonObject>("api/version"))!["version"]!.GetValue<string>(),
    pdf_sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(opt.Pdf))).ToLowerInvariant(),
    pages = pageTexts.Count, chunks = chunks.Count, index_build_s = indexSeconds,
    index_bytes = new FileInfo(indexPath).Length, index_bytes_basis = "index.db", conversation = opt.Conversation,
    langchain_packages = "0.17.0", commit = GitCommit(),
}, new JsonSerializerOptions { WriteIndented = true }));

static async Task<ChatResponse> Generate(OllamaChatModel chat, JsonNode cfg, IReadOnlyCollection<Message> messages)
{
    var gen = cfg["generation"]!;
    var settings = new OllamaChatSettings
    {
        Temperature = cfg["temperature"]!.GetValue<float>(),
        Seed = cfg["seed"]!.GetValue<int>(),
        NumPredict = gen["max_tokens"]?.GetValue<int>(),
        NumCtx = gen["num_ctx"]?.GetValue<int>(),
        StopSequences = gen["stop"]?.AsArray().Select(s => s!.GetValue<string>()).ToArray(),
        UseStreaming = false,
    };
    ChatResponse? last = null;
    await foreach (var r in chat.GenerateAsync(new ChatRequest { Messages = messages }, settings)) last = r;
    return last ?? throw new InvalidOperationException("empty reply from the model");
}

static async Task<string> Rewrite(OllamaChatModel chat, JsonNode cfg, string question, List<Message> history)
{
    var rw = cfg["query_rewriting"]!;
    var recent = history.Append(Message.Human(question)).TakeLast(rw["history_messages"]!.GetValue<int>());
    var text = string.Join("\n", recent.Select(m => $"{(m.Role == MessageRole.Human ? "user" : "assistant")}: {m.Content}"));
    var prompt = rw["template"]!.GetValue<string>().Replace("{history}", text).Replace("{question}", question);
    var plain = JsonNode.Parse(cfg.ToJsonString())!;
    plain["generation"] = new JsonObject { ["max_tokens"] = 200, ["stop"] = null };
    var role = rw["role"]?.GetValue<string>() == "system" ? MessageRole.System : MessageRole.Human;
    return (await Generate(chat, plain, new[] { new Message(prompt, role) })).LastMessageContent?.Trim() ?? question;
}

// "legacy" is the package's own call to /api/embeddings, which Ollama 0.35.1 refuses with HTTP 500 for input longer than
// the window. "embed" posts to /api/embed, which cuts the input to the window as older Ollama versions did.
async Task<float[][]> Embed(string[] texts)
{
    if (embedEndpoint == "legacy")
        return (await embedder.CreateEmbeddingsAsync(EmbeddingRequest.ToEmbeddingRequest(texts))).Values.ToArray();
    var reply = await http.PostAsJsonAsync("api/embed", new { model = cfg.Str("embedding_model"), input = texts });
    reply.EnsureSuccessStatusCode();
    var body = (await reply.Content.ReadFromJsonAsync<JsonObject>())!;
    return body["embeddings"]!.AsArray().Select(v => v!.AsArray().Select(x => x!.GetValue<float>()).ToArray()).ToArray();
}

static async Task<int?> ContextLength(HttpClient http, string model)
{
    var ps = await http.GetFromJsonAsync<JsonObject>("api/ps");
    foreach (var m in ps!["models"]?.AsArray() ?? new JsonArray())
        if (m!["name"]!.GetValue<string>().Split(':')[0] == model.Split(':')[0])
            return m["context_length"]?.GetValue<int>();
    return null;
}

static async Task<string?> Digest(HttpClient http, string model)
{
    var tags = await http.GetFromJsonAsync<JsonObject>("api/tags");
    foreach (var m in tags!["models"]!.AsArray())
    {
        var name = m!["name"]!.GetValue<string>();
        if (name == model || (!model.Contains(':') && name == model + ":latest")) return m["digest"]!.GetValue<string>();
    }
    return null;
}

static string? GitCommit()
{
    try
    {
        var p = Process.Start(new ProcessStartInfo("git", "rev-parse HEAD") { RedirectStandardOutput = true, RedirectStandardError = true })!;
        var s = p.StandardOutput.ReadToEnd().Trim();
        p.WaitForExit();
        return s.Length == 0 ? null : s;
    }
    catch { return null; }
}

record Chunk(string Id, List<int> Pages, string Text);

record Question(string Id, string Text, string SourcePages = "");

static class Questions
{
    public static List<Question> Read(Options o)
    {
        if (o.SingleQuestion is not null) return new() { new Question("q", o.SingleQuestion) };
        var lines = File.ReadAllText(o.QuestionsPath);
        var rows = Csv.Parse(lines);
        var head = rows[0];
        var iId = head.IndexOf("id");
        var iQ = head.IndexOf("question");
        var iP = head.IndexOf("source_pages");
        var list = rows.Skip(1).Where(r => r.Count > Math.Max(iId, iQ))
            .Select(r => new Question(r[iId], r[iQ], iP >= 0 && iP < r.Count ? r[iP] : "")).ToList();
        return o.Limit is int n ? list.Take(n).ToList() : list;
    }
}

static class Pages
{
    public static List<int> Parse(string text)
    {
        var pages = new SortedSet<int>();
        foreach (var part in text.Replace(',', ';').Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
        {
            var bits = part.Split('-');
            var lo = int.Parse(bits[0]);
            var hi = bits.Length > 1 ? int.Parse(bits[1]) : lo;
            for (var n = lo; n <= hi; n++) pages.Add(n);
        }
        return pages.ToList();
    }
}

static class Csv
{
    public static List<List<string>> Parse(string text)
    {
        var rows = new List<List<string>>();
        var row = new List<string>();
        var cur = new StringBuilder();
        var quoted = false;
        for (var i = 0; i < text.Length; i++)
        {
            var c = text[i];
            if (quoted)
            {
                if (c == '"' && i + 1 < text.Length && text[i + 1] == '"') { cur.Append('"'); i++; }
                else if (c == '"') quoted = false;
                else cur.Append(c);
            }
            else if (c == '"') quoted = true;
            else if (c == ',') { row.Add(cur.ToString()); cur.Clear(); }
            else if (c == '\n' || c == '\r')
            {
                if (c == '\r' && i + 1 < text.Length && text[i + 1] == '\n') i++;
                row.Add(cur.ToString()); cur.Clear();
                if (row.Count > 1 || row[0].Length > 0) rows.Add(row);
                row = new();
            }
            else cur.Append(c);
        }
        if (cur.Length > 0 || row.Count > 0) { row.Add(cur.ToString()); rows.Add(row); }
        return rows;
    }
}

static class Chunker
{
    public static List<Chunk> Build(JsonNode cfg, List<string> pages)
    {
        var c = cfg["chunking"]!;
        var kind = c["kind"]!.GetValue<string>();
        return kind switch
        {
            "page" => pages.Select((t, i) => new Chunk($"p{i + 1:0000}", new() { i + 1 }, t)).ToList(),
            "sentence_groups" => SentenceGroups(pages, c["max_chars"]!.GetValue<int>()),
            "procedure" => Procedures(pages, c["heading_pattern"]!.GetValue<string>(), c["step_pattern"]!.GetValue<string>(), c["max_chars"]!.GetValue<int>()),
            _ => throw new NotSupportedException($"chunking kind '{kind}' is not implemented"),
        };
    }

    static (string flat, List<int> starts) Flatten(List<string> pages)
    {
        var starts = new List<int>();
        var text = new StringBuilder();
        foreach (var p in pages)
        {
            starts.Add(text.Length);
            text.Append(Regex.Replace(p, @"\s+", " ").Trim()).Append(' ');
        }
        return (text.ToString().Trim(), starts);
    }

    static List<Chunk> ToChunks(string prefix, string flat, List<int> starts, IEnumerable<(int s, int e)> spans) =>
        spans.Select((g, i) =>
        {
            var first = starts.FindLastIndex(x => x <= g.s);
            var last = starts.FindLastIndex(x => x <= Math.Max(g.s, g.e - 1));
            return new Chunk($"{prefix}{i:0000}", Enumerable.Range(first + 1, last - first + 1).ToList(), flat[g.s..g.e]);
        }).ToList();

    // Same grouping as Implementation A, including its quirk: sentences inside a chunk are joined without a space,
    // as in the upstream upload script. A chunking experiment on B then changes only where the chunks are cut.
    static List<Chunk> SentenceGroups(List<string> pages, int maxChars)
    {
        var (flat, starts) = Flatten(pages);
        var spans = new List<(int s, int e)>();
        var start = 0;
        foreach (Match m in Regex.Matches(flat, @"(?<=[.!?]) +"))
        {
            spans.Add((start, m.Index));
            start = m.Index + m.Length;
        }
        spans.Add((start, flat.Length));
        var bodies = new List<(string text, int s, int e)>();
        var cur = "";
        int first = 0, last = 0;
        var open = false;
        void Close() { if (cur.Trim().Length > 0) bodies.Add((cur.Trim(), first, last)); }
        foreach (var (s, e) in spans.Where(x => x.e > x.s))
        {
            var sentence = flat[s..e];
            if (cur.Length + sentence.Length + 1 < maxChars)
            {
                cur += (sentence + " ").Trim();
                if (!open) { first = s; open = true; }
                last = e;
            }
            else
            {
                Close();
                cur = sentence + " ";
                first = s;
                last = e;
                open = true;
            }
        }
        Close();
        return bodies.Select((g, i) =>
        {
            var a = starts.FindLastIndex(x => x <= g.s);
            var b = starts.FindLastIndex(x => x <= Math.Max(g.s, g.e - 1));
            return new Chunk($"c{i:0000}", Enumerable.Range(a + 1, b - a + 1).ToList(), g.text);
        }).ToList();
    }

    // One chunk per heading, so a procedure keeps its prerequisites and steps together even across pages.
    // A section longer than maxChars is cut at step boundaries.
    static List<Chunk> Procedures(List<string> pages, string headingPattern, string stepPattern, int maxChars)
    {
        var (flat, starts) = Flatten(pages);
        var cuts = Regex.Matches(flat, headingPattern).Select(m => m.Index).Where(i => i > 0).Prepend(0).Distinct().OrderBy(i => i).ToList();
        cuts.Add(flat.Length);
        var spans = new List<(int s, int e)>();
        for (var i = 0; i + 1 < cuts.Count; i++)
        {
            var (s, e) = (cuts[i], cuts[i + 1]);
            while (e - s > maxChars)
            {
                var step = Regex.Matches(flat[s..e], stepPattern).Select(m => s + m.Index).LastOrDefault(x => x > s && x - s <= maxChars);
                var cut = step > s ? step : s + maxChars;
                spans.Add((s, cut));
                s = cut;
            }
            spans.Add((s, e));
        }
        return ToChunks("h", flat, starts, spans.Select(x => (x.s, x.e - (flat[x.e - 1] == ' ' ? 1 : 0))).Where(x => x.Item2 > x.s));
    }
}

static class Config
{
    public static JsonNode Load(string path, string section, IEnumerable<string> overrides)
    {
        var root = JsonNode.Parse(File.ReadAllText(path))!;
        var merged = new JsonObject();
        foreach (var kv in root["common"]!.AsObject()) merged[kv.Key] = kv.Value?.DeepClone();
        foreach (var kv in root[section]!.AsObject()) merged[kv.Key] = kv.Value?.DeepClone();
        foreach (var o in overrides)
        {
            var eq = o.IndexOf('=');
            var parts = o[..eq].Split('.');
            JsonNode node = merged;
            foreach (var p in parts[..^1]) node = node[p]!;
            node[parts[^1]] = JsonNode.Parse(o[(eq + 1)..]);
        }
        return merged;
    }

    public static string Str(this JsonNode cfg, string key) => cfg[key]!.GetValue<string>();
}

record Options(string Pdf, string Model, string Ollama, string QuestionsPath, string? SingleQuestion, string Out,
               string ConfigPath, List<string> Overrides, string Conversation, bool RetrievalOnly, int? Limit)
{
    public static Options Parse(string[] a)
    {
        string Get(string name, string? fallback = null)
        {
            var i = Array.IndexOf(a, name);
            return i >= 0 ? a[i + 1] : fallback ?? throw new ArgumentException($"missing {name}");
        }
        var overrides = new List<string>();
        for (var i = 0; i < a.Length - 1; i++) if (a[i] == "--set") overrides.Add(a[i + 1]);
        var single = Array.IndexOf(a, "--question") >= 0 ? Get("--question") : null;
        var limit = Array.IndexOf(a, "--limit") >= 0 ? int.Parse(Get("--limit")) : (int?)null;
        return new Options(Get("--pdf"), Get("--model", "llama3:latest"), Get("--ollama", "http://localhost:11434"),
            Get("--questions", "questions/questions.csv"), single, Get("--out"), Get("--config", "config/pipelines.json"),
            overrides, Get("--conversation", "fresh"), a.Contains("--retrieval-only"), limit);
    }
}
