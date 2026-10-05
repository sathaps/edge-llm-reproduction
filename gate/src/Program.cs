// Program.cs: exercises the gate against a set of model-style proposals and prints each decision.
// The state reader here is a stand-in; in the control application it would read from the
// same trusted source the operator interface uses.

using EdgeGate;

var state = new FakeState(running: true, values: new() { ["PressureSetpoint"] = 5000, ["RateSetpoint"] = 8.0 });

var envelope = new GateEnvelope
{
    Setpoints =
    {
        ["PressureSetpoint"] = new SetpointLimit(Low: 0, High: 9000, MaxStep: 500),
        ["RateSetpoint"]     = new SetpointLimit(Low: 0, High: 12, MaxStep: 1.0),
    },
    ModeTags = { "UnitMode" },
    AllowedModes = { "Idle", "Standby" },
    MaxActionsPerWindow = 3,
    Window = TimeSpan.FromMinutes(10),
    MaxCumulativeChangePerWindow = 1.5,
};

var gate = new DeterministicGate(envelope, state, new JsonLinesAuditSink("gate_audit.jsonl"));

string[] proposals =
{
    """{ "kind": "SetSetpoint", "tag": "RateSetpoint", "value": 8.5, "rationale": "reduce load gradually" }""",
    """{ "kind": "SetSetpoint", "tag": "PressureSetpoint", "value": 9500 }""",
    """{ "kind": "SetSetpoint", "tag": "PressureSetpoint", "value": 6000 }""",
    """{ "kind": "SetSetpoint", "tag": "RateSetpoint", "value": 9.0 }""",
    """{ "kind": "SetSetpoint", "tag": "RateSetpoint", "value": 8.7 }""",
    """{ "kind": "ChangeMode", "tag": "UnitMode", "mode": "Idle" }""",
    """{ "kind": "InhibitTrip", "tag": "HighPressureTrip" }""",
    """{ "kind": "SetSetpoint", "tag": "ValveOpen", "value": 1 }""",
    """{ "kind": "OpenValve", "tag": "V-101" }""",
    """{ "kind": "SetSetpoint", "tag": "RateSetpoint", "value": 8.2, "force": true }""",
    """Sure! I would set the rate to 8.2.""",
};

foreach (var json in proposals)
{
    var d = gate.Evaluate(json);
    Console.WriteLine($"{(d.Accepted ? "ACCEPT" : "REFUSE"),-7} {d.ReasonCode,-26} {d.Detail}");
}

// Recheck at execution: the first accepted proposal is re-evaluated after the state has moved.
var first = new ActionProposal { Kind = ActionKind.SetSetpoint, Tag = "RateSetpoint", Value = 8.5 };
state.Values["RateSetpoint"] = 6.0; // a step of 2.5 is now larger than MaxStep
var r = gate.RecheckBeforeExecution(first);
Console.WriteLine($"RECHECK {r.ReasonCode,-26} {r.Detail}");

sealed class FakeState : ITrustedStateReader
{
    private readonly bool _running;
    public Dictionary<string, double> Values { get; }
    public FakeState(bool running, Dictionary<string, double> values) { _running = running; Values = values; }
    public bool TryReadNumber(string tag, out double value) => Values.TryGetValue(tag, out value);
    public bool IsUnitRunning() => _running;
}
