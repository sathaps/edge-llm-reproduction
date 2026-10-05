// usage: dotnet run --project gate/scripted -- <proposals.json> <out-dir>

using System.Text;
using System.Text.Json;
using EdgeGate;

var file = args.Length > 0 ? args[0] : "gate/proposals/scripted.json";
var outDir = args.Length > 1 ? args[1] : "results/gate";
Directory.CreateDirectory(outDir);

var doc = JsonDocument.Parse(File.ReadAllText(file)).RootElement;
var rows = new List<(string scenario, string id, string raw, bool accepted, string reason, string expect, string detail)>();
var clock = new Clock();

foreach (var s in doc.GetProperty("scenarios").EnumerateArray())
{
    var state = new State { Running = s.GetProperty("running").GetBoolean() };
    foreach (var kv in s.GetProperty("values").EnumerateObject()) state.Values[kv.Name] = kv.Value.GetDouble();

    var maxCum = s.GetProperty("maxCumulative");
    var env = new GateEnvelope
    {
        Setpoints =
        {
            ["PressureSetpoint"] = new SetpointLimit(Low: 0, High: 9000, MaxStep: 500),
            ["RateSetpoint"]     = new SetpointLimit(Low: 0, High: 12, MaxStep: 1.0),
            ["NoStateTag"]       = new SetpointLimit(Low: 0, High: 10, MaxStep: 5),
        },
        ModeTags = { "UnitMode" },
        AllowedModes = { "Idle", "Standby" },
        MaxActionsPerWindow = s.GetProperty("maxActions").GetInt32(),
        Window = TimeSpan.FromMinutes(10),
        MaxCumulativeChangePerWindow = maxCum.ValueKind == JsonValueKind.Null ? double.PositiveInfinity : maxCum.GetDouble(),
    };
    clock.Now = new DateTime(2026, 1, 1, 0, 0, 0, DateTimeKind.Utc);
    var gate = new DeterministicGate(env, state, new NullSink(), () => clock.Now);
    var sid = s.GetProperty("id").GetString()!;

    foreach (var step in s.GetProperty("steps").EnumerateArray())
    {
        if (step.TryGetProperty("advanceMinutes", out var adv)) clock.Now += TimeSpan.FromMinutes(adv.GetDouble());
        if (step.TryGetProperty("setValues", out var sv))
            foreach (var kv in sv.EnumerateObject()) state.Values[kv.Name] = kv.Value.GetDouble();
        GateDecision d;
        string raw;
        if (step.TryGetProperty("recheck", out var rc))
        {
            var p = JsonSerializer.Deserialize<ActionProposal>(rc.GetRawText(),
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true, Converters = { new System.Text.Json.Serialization.JsonStringEnumConverter() } })!;
            d = gate.RecheckBeforeExecution(p);
            raw = "RECHECK " + rc.GetRawText();
        }
        else
        {
            raw = step.GetProperty("raw").GetString()!;
            d = gate.Evaluate(raw);
        }
        rows.Add((sid, step.GetProperty("id").GetString()!, raw, d.Accepted, d.ReasonCode,
                  step.GetProperty("expect").GetString()!, d.Detail));
    }
}

static string Csv(string v) => "\"" + v.Replace("\"", "\"\"").Replace("\r", "").Replace("\n", "\\n") + "\"";

var sb = new StringBuilder("scenario,id,accepted,reason_code,expected,matches_expected,raw_input,detail\n");
foreach (var r in rows)
    sb.AppendLine(string.Join(",", Csv(r.scenario), Csv(r.id), r.accepted ? "true" : "false", r.reason, r.expect,
                              r.reason == r.expect ? "true" : "false", Csv(r.raw), Csv(r.detail)));
File.WriteAllText(Path.Combine(outDir, "scripted_proposals.csv"), sb.ToString());

var counts = rows.GroupBy(r => r.reason).OrderBy(g => g.Key == Reason.Accepted ? "" : g.Key);
var cb = new StringBuilder("reason_code,count\n");
foreach (var g in counts) cb.AppendLine($"{g.Key},{g.Count()}");
cb.AppendLine($"TOTAL,{rows.Count}");
File.WriteAllText(Path.Combine(outDir, "scripted_counts.csv"), cb.ToString());

Console.WriteLine(cb.ToString());
var mism = rows.Where(r => r.reason != r.expect).ToList();
Console.WriteLine($"proposals: {rows.Count}; accepted: {rows.Count(r => r.accepted)}; refused: {rows.Count(r => !r.accepted)}; mismatches vs expected: {mism.Count}");
foreach (var m in mism) Console.WriteLine($"MISMATCH {m.scenario}/{m.id}: got {m.reason}, expected {m.expect} :: {m.detail}");
var reasons = typeof(Reason).GetFields().Select(f => (string)f.GetRawConstantValue()!).ToHashSet();
var missing = reasons.Except(rows.Select(r => r.reason)).ToList();
Console.WriteLine(missing.Count == 0 ? "every reason code occurs at least once" : "reason codes never produced: " + string.Join(", ", missing));

sealed class NullSink : IAuditSink { public void Write(GateDecision d) { } }
sealed class Clock { public DateTime Now { get; set; } }
sealed class State : ITrustedStateReader
{
    public bool Running { get; set; }
    public Dictionary<string, double> Values { get; } = new();
    public bool TryReadNumber(string tag, out double value) => Values.TryGetValue(tag, out value);
    public bool IsUnitRunning() => Running;
}
