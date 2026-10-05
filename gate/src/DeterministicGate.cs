// DeterministicGate.cs
// A small, hand-written gate that sits between the reasoning layer and the tool surface.
// The model may only *propose* an action as JSON. The gate parses it against a strict schema,
// checks it against an envelope and trusted plant state, and either accepts it or refuses it
// with a reason code. Every decision is written to an append-only audit log.
// Deny by default: anything not explicitly allowed is refused.

using System.Text.Json;
using System.Text.Json.Serialization;

namespace EdgeGate;

// ---------- Proposal schema (what the model is allowed to say) ----------

public enum ActionKind { SetSetpoint, ChangeMode, InhibitTrip }

public sealed class ActionProposal
{
    [JsonRequired] public ActionKind Kind { get; init; }
    [JsonRequired] public string Tag { get; init; } = "";
    public double? Value { get; init; }        // SetSetpoint
    public string? Mode { get; init; }         // ChangeMode
    public string? Rationale { get; init; }    // free text, logged only, never interpreted
}

// ---------- Envelope (written by engineering, not by the model) ----------

public sealed record SetpointLimit(double Low, double High, double MaxStep);

public sealed class GateEnvelope
{
    public Dictionary<string, SetpointLimit> Setpoints { get; init; } = new();
    public HashSet<string> ModeTags { get; init; } = new();
    public HashSet<string> AllowedModes { get; init; } = new();
    public int MaxActionsPerWindow { get; init; } = 3;
    public TimeSpan Window { get; init; } = TimeSpan.FromMinutes(10);
    public double MaxCumulativeChangePerWindow { get; init; } = double.PositiveInfinity; // per tag
}

// ---------- Trusted state (read from the control system, never from the model) ----------

public interface ITrustedStateReader
{
    bool TryReadNumber(string tag, out double value);
    bool IsUnitRunning();
}

// ---------- Decisions and audit ----------

public static class Reason
{
    public const string Accepted = "ACCEPTED";
    public const string SchemaInvalid = "SCHEMA_INVALID";
    public const string TagNotWritable = "TAG_NOT_WRITABLE";
    public const string ValueMissing = "VALUE_MISSING";
    public const string AboveHighLimit = "ABOVE_HIGH_LIMIT";
    public const string BelowLowLimit = "BELOW_LOW_LIMIT";
    public const string StepTooLarge = "STEP_TOO_LARGE";
    public const string StateUnavailable = "STATE_UNAVAILABLE";
    public const string ModeNotAllowed = "MODE_NOT_ALLOWED";
    public const string ModeChangeWhileRunning = "MODE_CHANGE_WHILE_RUNNING";
    public const string TripInhibitForbidden = "TRIP_INHIBIT_FORBIDDEN";
    public const string RateLimit = "RATE_LIMIT";
    public const string CumulativeLimit = "CUMULATIVE_LIMIT";
    public const string StateChanged = "STATE_CHANGED_BEFORE_EXECUTION";
}

public sealed record GateDecision(Guid Id, DateTime UtcTime, bool Accepted, string ReasonCode,
                                  string Detail, ActionProposal? Proposal);

public interface IAuditSink { void Write(GateDecision decision); }

public sealed class JsonLinesAuditSink : IAuditSink
{
    private readonly string _path;
    private readonly object _lock = new();
    public JsonLinesAuditSink(string path) => _path = path;
    public void Write(GateDecision d)
    {
        var line = JsonSerializer.Serialize(d, DeterministicGate.JsonOptions);
        lock (_lock) File.AppendAllText(_path, line + Environment.NewLine);
    }
}

// ---------- The gate ----------

public sealed class DeterministicGate
{
    internal static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow, // unknown fields are refused
        Converters = { new JsonStringEnumConverter(allowIntegerValues: false) },
    };

    private readonly GateEnvelope _env;
    private readonly ITrustedStateReader _state;
    private readonly IAuditSink _audit;
    private readonly Func<DateTime> _clock;
    private readonly List<(DateTime t, string tag, double delta)> _accepted = new();

    public DeterministicGate(GateEnvelope env, ITrustedStateReader state, IAuditSink audit,
                             Func<DateTime>? clock = null)
    {
        _env = env; _state = state; _audit = audit; _clock = clock ?? (() => DateTime.UtcNow);
    }

    /// <summary>Evaluate raw model output. Anything that does not parse to the schema is refused.</summary>
    public GateDecision Evaluate(string modelJson)
    {
        ActionProposal? p;
        try { p = JsonSerializer.Deserialize<ActionProposal>(modelJson, JsonOptions); }
        catch (Exception ex) { return Log(Refuse(Reason.SchemaInvalid, ex.Message, null)); }
        if (p is null || string.IsNullOrWhiteSpace(p.Tag))
            return Log(Refuse(Reason.SchemaInvalid, "empty proposal or tag", p));
        return Evaluate(p);
    }

    /// <summary>Evaluate a typed proposal and, if accepted, count it against the rate and cumulative bounds.</summary>
    public GateDecision Evaluate(ActionProposal p)
    {
        var d = Check(p, countBounds: true);
        if (d.Accepted) _accepted.Add((_clock(), p.Tag, Delta(p)));
        return Log(d);
    }

    /// <summary>Repeat the envelope and state checks at the moment of execution, since state may have moved.</summary>
    public GateDecision RecheckBeforeExecution(ActionProposal p)
    {
        var d = Check(p, countBounds: false);
        return Log(d.Accepted ? d : d with { ReasonCode = Reason.StateChanged, Detail = $"{d.ReasonCode}: {d.Detail}" });
    }

    private GateDecision Check(ActionProposal p, bool countBounds)
    {
        switch (p.Kind)
        {
            case ActionKind.InhibitTrip:
                return Refuse(Reason.TripInhibitForbidden, "the gate never inhibits a trip", p);

            case ActionKind.SetSetpoint:
            {
                if (!_env.Setpoints.TryGetValue(p.Tag, out var lim))
                    return Refuse(Reason.TagNotWritable, $"'{p.Tag}' is not a writable setpoint", p);
                if (p.Value is not double v || double.IsNaN(v) || double.IsInfinity(v))
                    return Refuse(Reason.ValueMissing, "setpoint value missing or not finite", p);
                if (v > lim.High) return Refuse(Reason.AboveHighLimit, $"{v} > high limit {lim.High}", p);
                if (v < lim.Low) return Refuse(Reason.BelowLowLimit, $"{v} < low limit {lim.Low}", p);
                if (!_state.TryReadNumber(p.Tag, out var current))
                    return Refuse(Reason.StateUnavailable, $"cannot read current value of '{p.Tag}'", p);
                if (Math.Abs(v - current) > lim.MaxStep)
                    return Refuse(Reason.StepTooLarge, $"step {Math.Abs(v - current)} > max step {lim.MaxStep}", p);
                break;
            }

            case ActionKind.ChangeMode:
                if (!_env.ModeTags.Contains(p.Tag))
                    return Refuse(Reason.TagNotWritable, $"'{p.Tag}' is not a writable mode tag", p);
                if (p.Mode is null || !_env.AllowedModes.Contains(p.Mode))
                    return Refuse(Reason.ModeNotAllowed, $"mode '{p.Mode}' is not allowed", p);
                if (_state.IsUnitRunning())
                    return Refuse(Reason.ModeChangeWhileRunning, "unit is running", p);
                break;

            default:
                return Refuse(Reason.SchemaInvalid, $"unknown action kind {p.Kind}", p);
        }

        if (countBounds)
        {
            var since = _clock() - _env.Window;
            _accepted.RemoveAll(a => a.t < since);
            if (_accepted.Count >= _env.MaxActionsPerWindow)
                return Refuse(Reason.RateLimit, $"{_accepted.Count} actions already accepted in window", p);
            var cumulative = _accepted.Where(a => a.tag == p.Tag).Sum(a => Math.Abs(a.delta)) + Math.Abs(Delta(p));
            if (cumulative > _env.MaxCumulativeChangePerWindow)
                return Refuse(Reason.CumulativeLimit, $"cumulative change {cumulative:0.###} on '{p.Tag}' exceeds bound", p);
        }

        return new GateDecision(Guid.NewGuid(), _clock(), true, Reason.Accepted, "within envelope", p);
    }

    private double Delta(ActionProposal p) =>
        p.Kind == ActionKind.SetSetpoint && p.Value is double v && _state.TryReadNumber(p.Tag, out var cur)
            ? v - cur : 0.0;

    private GateDecision Refuse(string code, string detail, ActionProposal? p) =>
        new(Guid.NewGuid(), _clock(), false, code, detail, p);

    private GateDecision Log(GateDecision d) { _audit.Write(d); return d; }
}
