// usage: dotnet run --project gate/modelrun -- --requests gate/proposals/requests.json --model llama3:latest --out DIR
//        [--ollama URL] [--schema gate/proposals/schema_prompt.txt]
// Each request goes to the model with the action schema. The raw reply is passed to DeterministicGate.Evaluate(string).
// Every request gets a fresh gate, so the rate and cumulative bounds do not couple requests.

using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using EdgeGate;
using ModelRun;

string Arg(string name, string? fallback = null)
{
    var i = Array.IndexOf(args, name);
    return i >= 0 ? args[i + 1] : fallback ?? throw new ArgumentException($"missing {name}");
}

var requestsPath = Arg("--requests");
var model = Arg("--model");
var ollama = Arg("--ollama", "http://localhost:11434").TrimEnd('/');
var outDir = Arg("--out");
var schema = File.ReadAllText(Arg("--schema", "gate/proposals/schema_prompt.txt"));
Directory.CreateDirectory(outDir);

var requests = JsonNode.Parse(File.ReadAllText(requestsPath))!["requests"]!.AsArray();
using var http = new HttpClient { BaseAddress = new Uri(ollama + "/"), Timeout = TimeSpan.FromHours(1) };

var csv = new StringBuilder("model,request_id,group,raw_output,parsed,accepted,reason_code,accepted_outside_envelope,eval_count,done_reason\n");
var byReason = new SortedDictionary<string, int>();
int total = 0, parsed = 0, accepted = 0, outside = 0;

foreach (var r in requests)
{
    var body = new JsonObject
    {
        ["model"] = model, ["stream"] = false,
        ["messages"] = new JsonArray(
            new JsonObject { ["role"] = "system", ["content"] = schema },
            new JsonObject { ["role"] = "user", ["content"] = r!["text"]!.GetValue<string>() }),
        ["options"] = new JsonObject { ["temperature"] = 0, ["seed"] = 42 },
    };
    var reply = await (await http.PostAsJsonAsync("api/chat", body)).Content.ReadFromJsonAsync<JsonObject>();
    var raw = reply!["message"]!["content"]!.GetValue<string>();

    var gate = new DeterministicGate(GroundTruth.Envelope(), new FixedState(), new NullSink());
    var d = gate.Evaluate(raw);
    var isParsed = d.ReasonCode != Reason.SchemaInvalid;
    var bad = d.Accepted && d.Proposal is { } p && GroundTruth.Violates(p);

    total++; parsed += isParsed ? 1 : 0; accepted += d.Accepted ? 1 : 0; outside += bad ? 1 : 0;
    byReason[d.ReasonCode] = byReason.GetValueOrDefault(d.ReasonCode) + 1;
    csv.AppendLine(string.Join(",", Q(model), Q(r["id"]!.GetValue<string>()), Q(r["group"]!.GetValue<string>()), Q(raw),
        isParsed ? "true" : "false", d.Accepted ? "true" : "false", d.ReasonCode, bad ? "true" : "false",
        reply["eval_count"]?.ToString() ?? "", Q(reply["done_reason"]?.ToString() ?? "")));
}

File.WriteAllText(Path.Combine(outDir, "gate_model.csv"), csv.ToString());
var summary = new
{
    model, requests = Path.GetFileName(requestsPath), total, parsed, accepted, refused = total - accepted,
    accepted_outside_envelope = outside, by_reason_code = byReason,
};
File.WriteAllText(Path.Combine(outDir, "gate_model_summary.json"), JsonSerializer.Serialize(summary, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine($"{model}: {parsed} of {total} parsed, {accepted} of {total} accepted, {total - accepted} of {total} refused, {outside} accepted outside the envelope");
foreach (var (k, v) in byReason) Console.WriteLine($"  {k}: {v}");

static string Q(string s) => "\"" + s.Replace("\"", "\"\"").Replace("\r", "").Replace("\n", "\\n") + "\"";
