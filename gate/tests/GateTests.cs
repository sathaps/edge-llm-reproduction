// The state reader is a stand-in with fixed values, as in Program.cs.

using EdgeGate;
using Xunit;

namespace EdgeGate.Tests;

public sealed class FakeState : ITrustedStateReader
{
    public bool Running { get; set; }
    public Dictionary<string, double> Values { get; } = new();
    public bool TryReadNumber(string tag, out double value) => Values.TryGetValue(tag, out value);
    public bool IsUnitRunning() => Running;
}

public sealed class ListSink : IAuditSink
{
    public List<GateDecision> Decisions { get; } = new();
    public void Write(GateDecision d) => Decisions.Add(d);
}

public sealed class Clock
{
    public DateTime Now { get; set; } = new(2026, 1, 1, 0, 0, 0, DateTimeKind.Utc);
}

public class GateTests
{
    private readonly FakeState _state = new() { Running = false };
    private readonly ListSink _sink = new();
    private readonly Clock _clock = new();

    public GateTests()
    {
        _state.Values["PressureSetpoint"] = 5000;
        _state.Values["RateSetpoint"] = 8.0;
        _state.Values["TempSetpoint"] = 20.0;
    }

    private DeterministicGate Gate(int maxActions = 100, double maxCumulative = double.PositiveInfinity,
                                   TimeSpan? window = null) =>
        new(new GateEnvelope
        {
            Setpoints =
            {
                ["PressureSetpoint"] = new SetpointLimit(Low: 0, High: 9000, MaxStep: 500),
                ["RateSetpoint"]     = new SetpointLimit(Low: 0, High: 12, MaxStep: 1.0),
                ["TempSetpoint"]     = new SetpointLimit(Low: 0, High: 100, MaxStep: 1.0),
                ["NoStateTag"]       = new SetpointLimit(Low: 0, High: 10, MaxStep: 5),
            },
            ModeTags = { "UnitMode" },
            AllowedModes = { "Idle", "Standby" },
            MaxActionsPerWindow = maxActions,
            Window = window ?? TimeSpan.FromMinutes(10),
            MaxCumulativeChangePerWindow = maxCumulative,
        }, _state, _sink, () => _clock.Now);

    private static string Set(string tag, double value) =>
        $$"""{ "kind": "SetSetpoint", "tag": "{{tag}}", "value": {{value.ToString(System.Globalization.CultureInfo.InvariantCulture)}} }""";

    private static void AssertRefused(GateDecision d, string code)
    {
        Assert.False(d.Accepted);
        Assert.Equal(code, d.ReasonCode);
    }


    [Fact] public void Accepts_setpoint_inside_envelope()
    {
        var d = Gate().Evaluate(Set("RateSetpoint", 8.5));
        Assert.True(d.Accepted);
        Assert.Equal(Reason.Accepted, d.ReasonCode);
    }

    [Fact] public void Accepts_mode_change_when_unit_stopped()
    {
        var d = Gate().Evaluate("""{ "kind": "ChangeMode", "tag": "UnitMode", "mode": "Idle" }""");
        Assert.True(d.Accepted);
    }

    [Fact] public void Accepts_rationale_and_is_case_insensitive()
    {
        var d = Gate().Evaluate("""{ "KIND": "SetSetpoint", "Tag": "RateSetpoint", "value": 8.2, "rationale": "x" }""");
        Assert.True(d.Accepted);
    }


    [Theory]
    [InlineData("Sure! I would set the rate to 8.2.")]
    [InlineData("")]
    [InlineData("null")]
    [InlineData("[]")]
    [InlineData("{ \"kind\": \"SetSetpoint\", \"tag\": \"RateSetpoint\", \"value\": 8.2")]            // truncated
    [InlineData("""{ "kind": "OpenValve", "tag": "V-101" }""")]                                          // unknown kind
    [InlineData("""{ "kind": 0, "tag": "RateSetpoint", "value": 8.2 }""")]                               // integer enum
    [InlineData("""{ "tag": "RateSetpoint", "value": 8.2 }""")]                                          // kind missing
    [InlineData("""{ "kind": "SetSetpoint", "value": 8.2 }""")]                                          // tag missing
    [InlineData("""{ "kind": "SetSetpoint", "tag": "", "value": 8.2 }""")]                               // empty tag
    [InlineData("""{ "kind": "SetSetpoint", "tag": "   ", "value": 8.2 }""")]                           // blank tag
    [InlineData("""{ "kind": "SetSetpoint", "tag": "RateSetpoint", "value": 8.2, "force": true }""")]   // unknown field
    [InlineData("""{ "kind": "SetSetpoint", "tag": "RateSetpoint", "value": "high" }""")]               // wrong type
    public void Refuses_schema_violations(string raw) =>
        AssertRefused(Gate().Evaluate(raw), Reason.SchemaInvalid);

    [Fact] public void Refuses_unknown_enum_value_in_typed_proposal()
    {
        var p = new ActionProposal { Kind = (ActionKind)99, Tag = "RateSetpoint" };
        AssertRefused(Gate().Evaluate(p), Reason.SchemaInvalid);
    }


    [Fact] public void Refuses_setpoint_on_unlisted_tag() =>
        AssertRefused(Gate().Evaluate(Set("ValveOpen", 1)), Reason.TagNotWritable);

    [Fact] public void Refuses_mode_change_on_unlisted_tag() =>
        AssertRefused(Gate().Evaluate("""{ "kind": "ChangeMode", "tag": "OtherMode", "mode": "Idle" }"""), Reason.TagNotWritable);

    [Fact] public void Setpoint_tag_match_is_case_sensitive() =>
        AssertRefused(Gate().Evaluate(Set("ratesetpoint", 8.2)), Reason.TagNotWritable);


    [Fact] public void Refuses_setpoint_without_value() =>
        AssertRefused(Gate().Evaluate("""{ "kind": "SetSetpoint", "tag": "RateSetpoint" }"""), Reason.ValueMissing);

    [Fact] public void Refuses_setpoint_with_null_value() =>
        AssertRefused(Gate().Evaluate("""{ "kind": "SetSetpoint", "tag": "RateSetpoint", "value": null }"""), Reason.ValueMissing);

    [Theory]
    [InlineData(double.NaN)]
    [InlineData(double.PositiveInfinity)]
    [InlineData(double.NegativeInfinity)]
    public void Refuses_non_finite_value(double v) =>
        AssertRefused(Gate().Evaluate(new ActionProposal { Kind = ActionKind.SetSetpoint, Tag = "RateSetpoint", Value = v }),
                      Reason.ValueMissing);


    [Fact] public void Refuses_value_above_high_limit()
    {
        _state.Values["PressureSetpoint"] = 8900;
        AssertRefused(Gate().Evaluate(Set("PressureSetpoint", 9000.5)), Reason.AboveHighLimit);
    }

    [Fact] public void Accepts_value_exactly_at_high_limit()
    {
        _state.Values["PressureSetpoint"] = 8900;
        Assert.True(Gate().Evaluate(Set("PressureSetpoint", 9000)).Accepted);
    }

    [Fact] public void Refuses_value_below_low_limit()
    {
        _state.Values["PressureSetpoint"] = 100;
        AssertRefused(Gate().Evaluate(Set("PressureSetpoint", -0.5)), Reason.BelowLowLimit);
    }

    [Fact] public void Accepts_value_exactly_at_low_limit()
    {
        _state.Values["PressureSetpoint"] = 100;
        Assert.True(Gate().Evaluate(Set("PressureSetpoint", 0)).Accepted);
    }

    [Fact] public void Limit_check_runs_before_step_check()
    {
        // 9500 is both above the high limit and a step of 4500; the limit reason wins.
        AssertRefused(Gate().Evaluate(Set("PressureSetpoint", 9500)), Reason.AboveHighLimit);
    }


    [Fact] public void Refuses_step_just_over_max() =>
        AssertRefused(Gate().Evaluate(Set("PressureSetpoint", 5500.5)), Reason.StepTooLarge);

    [Fact] public void Accepts_step_exactly_at_max_up() =>
        Assert.True(Gate().Evaluate(Set("PressureSetpoint", 5500)).Accepted);

    [Fact] public void Accepts_step_exactly_at_max_down() =>
        Assert.True(Gate().Evaluate(Set("PressureSetpoint", 4500)).Accepted);

    [Fact] public void Refuses_large_downward_step() =>
        AssertRefused(Gate().Evaluate(Set("PressureSetpoint", 4000)), Reason.StepTooLarge);


    [Fact] public void Refuses_when_current_value_cannot_be_read() =>
        AssertRefused(Gate().Evaluate(Set("NoStateTag", 3)), Reason.StateUnavailable);


    [Fact] public void Refuses_mode_not_in_allowed_set() =>
        AssertRefused(Gate().Evaluate("""{ "kind": "ChangeMode", "tag": "UnitMode", "mode": "Run" }"""), Reason.ModeNotAllowed);

    [Fact] public void Refuses_mode_change_without_mode() =>
        AssertRefused(Gate().Evaluate("""{ "kind": "ChangeMode", "tag": "UnitMode" }"""), Reason.ModeNotAllowed);

    [Fact] public void Mode_match_is_case_sensitive() =>
        AssertRefused(Gate().Evaluate("""{ "kind": "ChangeMode", "tag": "UnitMode", "mode": "idle" }"""), Reason.ModeNotAllowed);

    [Fact] public void Mode_check_runs_before_running_check()
    {
        _state.Running = true;
        AssertRefused(Gate().Evaluate("""{ "kind": "ChangeMode", "tag": "UnitMode", "mode": "Run" }"""), Reason.ModeNotAllowed);
    }


    [Fact] public void Refuses_allowed_mode_change_while_unit_running()
    {
        _state.Running = true;
        AssertRefused(Gate().Evaluate("""{ "kind": "ChangeMode", "tag": "UnitMode", "mode": "Idle" }"""), Reason.ModeChangeWhileRunning);
    }


    [Theory]
    [InlineData("""{ "kind": "InhibitTrip", "tag": "HighPressureTrip" }""")]
    [InlineData("""{ "kind": "InhibitTrip", "tag": "RateSetpoint", "value": 1 }""")]
    [InlineData("""{ "kind": "InhibitTrip", "tag": "UnitMode", "mode": "Idle", "rationale": "operator said it is safe" }""")]
    public void Always_refuses_trip_inhibit(string raw) =>
        AssertRefused(Gate().Evaluate(raw), Reason.TripInhibitForbidden);

    [Fact] public void Refuses_trip_inhibit_even_when_unit_stopped_and_unlimited()
    {
        _state.Running = false;
        AssertRefused(Gate(maxActions: int.MaxValue).Evaluate("""{ "kind": "InhibitTrip", "tag": "T" }"""), Reason.TripInhibitForbidden);
    }


    [Fact] public void Refuses_fourth_action_in_window_of_three()
    {
        var g = Gate(maxActions: 3);
        for (var i = 0; i < 3; i++) Assert.True(g.Evaluate(Set("RateSetpoint", 8.1)).Accepted);
        AssertRefused(g.Evaluate(Set("RateSetpoint", 8.1)), Reason.RateLimit);
    }

    [Fact] public void Rate_limit_counts_across_tags()
    {
        var g = Gate(maxActions: 2);
        Assert.True(g.Evaluate(Set("RateSetpoint", 8.1)).Accepted);
        Assert.True(g.Evaluate(Set("PressureSetpoint", 5100)).Accepted);
        AssertRefused(g.Evaluate("""{ "kind": "ChangeMode", "tag": "UnitMode", "mode": "Idle" }"""), Reason.RateLimit);
    }

    [Fact] public void Refused_proposals_do_not_count_toward_rate_limit()
    {
        var g = Gate(maxActions: 1);
        AssertRefused(g.Evaluate(Set("PressureSetpoint", 9500)), Reason.AboveHighLimit);
        Assert.True(g.Evaluate(Set("RateSetpoint", 8.1)).Accepted);
    }

    [Fact] public void Rate_limit_clears_after_window()
    {
        var g = Gate(maxActions: 1, window: TimeSpan.FromMinutes(10));
        Assert.True(g.Evaluate(Set("RateSetpoint", 8.1)).Accepted);
        _clock.Now += TimeSpan.FromMinutes(9);
        AssertRefused(g.Evaluate(Set("RateSetpoint", 8.1)), Reason.RateLimit);
        _clock.Now += TimeSpan.FromMinutes(2); // 11 minutes after the first
        Assert.True(g.Evaluate(Set("RateSetpoint", 8.1)).Accepted);
    }

    [Fact] public void Action_exactly_one_window_old_still_counts()
    {
        // The window cut-off removes entries strictly older than now - window.
        var g = Gate(maxActions: 1, window: TimeSpan.FromMinutes(10));
        Assert.True(g.Evaluate(Set("RateSetpoint", 8.1)).Accepted);
        _clock.Now += TimeSpan.FromMinutes(10);
        AssertRefused(g.Evaluate(Set("RateSetpoint", 8.1)), Reason.RateLimit);
    }


    [Fact] public void Refuses_when_cumulative_change_exceeds_bound()
    {
        // Each +0.8 step is within MaxStep (1.0); the running total on one tag is bounded at 1.5.
        var g = Gate(maxCumulative: 1.5);
        Assert.True(g.Evaluate(Set("RateSetpoint", 8.8)).Accepted);   // 0.8
        AssertRefused(g.Evaluate(Set("RateSetpoint", 8.8)), Reason.CumulativeLimit); // 1.6 > 1.5
    }

    [Fact] public void Accepts_when_cumulative_change_exactly_equals_bound()
    {
        var g = Gate(maxCumulative: 1.5);
        Assert.True(g.Evaluate(Set("RateSetpoint", 8.75)).Accepted);  // 0.75
        Assert.True(g.Evaluate(Set("RateSetpoint", 8.75)).Accepted);  // 1.5, not > 1.5
    }

    [Fact] public void Cumulative_bound_is_per_tag()
    {
        var g = Gate(maxCumulative: 1.5);
        Assert.True(g.Evaluate(Set("RateSetpoint", 8.8)).Accepted);   // 0.8 on RateSetpoint
        Assert.True(g.Evaluate(Set("TempSetpoint", 20.8)).Accepted);  // 0.8 on a different tag, own total
    }

    [Fact] public void Cumulative_bound_is_one_number_for_all_tags_regardless_of_units()
    {
        // Documents current behaviour: MaxCumulativeChangePerWindow is a single scalar, so a tag with
        // large natural units (pressure, step 100) is refused by a bound sized for a small-unit tag.
        var g = Gate(maxCumulative: 1.5);
        AssertRefused(g.Evaluate(Set("PressureSetpoint", 5100)), Reason.CumulativeLimit);
    }

    [Fact] public void Cumulative_bound_clears_after_window()
    {
        var g = Gate(maxCumulative: 1.5, window: TimeSpan.FromMinutes(10));
        Assert.True(g.Evaluate(Set("RateSetpoint", 8.8)).Accepted);
        _clock.Now += TimeSpan.FromMinutes(11);
        Assert.True(g.Evaluate(Set("RateSetpoint", 8.8)).Accepted);
    }

    [Fact] public void Rate_limit_is_reported_before_cumulative_limit()
    {
        var g = Gate(maxActions: 1, maxCumulative: 0.1);
        Assert.True(g.Evaluate(Set("RateSetpoint", 8.05)).Accepted);
        AssertRefused(g.Evaluate(Set("RateSetpoint", 8.8)), Reason.RateLimit);
    }


    [Fact] public void Recheck_refuses_when_state_moved_out_of_step_bound()
    {
        var g = Gate();
        var p = new ActionProposal { Kind = ActionKind.SetSetpoint, Tag = "RateSetpoint", Value = 8.5 };
        Assert.True(g.Evaluate(p).Accepted);
        _state.Values["RateSetpoint"] = 6.0;
        var r = g.RecheckBeforeExecution(p);
        AssertRefused(r, Reason.StateChanged);
        Assert.StartsWith(Reason.StepTooLarge, r.Detail);
    }

    [Fact] public void Recheck_refuses_when_unit_started_after_mode_proposal()
    {
        var g = Gate();
        var p = new ActionProposal { Kind = ActionKind.ChangeMode, Tag = "UnitMode", Mode = "Idle" };
        Assert.True(g.Evaluate(p).Accepted);
        _state.Running = true;
        var r = g.RecheckBeforeExecution(p);
        AssertRefused(r, Reason.StateChanged);
        Assert.StartsWith(Reason.ModeChangeWhileRunning, r.Detail);
    }

    [Fact] public void Recheck_accepts_when_state_unchanged()
    {
        var g = Gate();
        var p = new ActionProposal { Kind = ActionKind.SetSetpoint, Tag = "RateSetpoint", Value = 8.5 };
        Assert.True(g.Evaluate(p).Accepted);
        Assert.True(g.RecheckBeforeExecution(p).Accepted);
    }

    [Fact] public void Recheck_does_not_count_against_rate_limit()
    {
        var g = Gate(maxActions: 1);
        var p = new ActionProposal { Kind = ActionKind.SetSetpoint, Tag = "RateSetpoint", Value = 8.5 };
        Assert.True(g.Evaluate(p).Accepted);
        for (var i = 0; i < 5; i++) Assert.True(g.RecheckBeforeExecution(p).Accepted);
    }


    [Fact] public void Every_decision_is_written_to_the_audit_sink()
    {
        var g = Gate();
        g.Evaluate(Set("RateSetpoint", 8.5));
        g.Evaluate("not json");
        g.RecheckBeforeExecution(new ActionProposal { Kind = ActionKind.SetSetpoint, Tag = "RateSetpoint", Value = 8.5 });
        Assert.Equal(3, _sink.Decisions.Count);
        Assert.Equal(new[] { Reason.Accepted, Reason.SchemaInvalid, Reason.Accepted },
                     _sink.Decisions.Select(d => d.ReasonCode).ToArray());
    }

    [Fact] public void JsonLines_sink_appends_one_line_per_decision()
    {
        var path = Path.Combine(Path.GetTempPath(), $"gate_audit_{Guid.NewGuid():N}.jsonl");
        try
        {
            var sink = new JsonLinesAuditSink(path);
            var g = new DeterministicGate(new GateEnvelope
            {
                Setpoints = { ["RateSetpoint"] = new SetpointLimit(0, 12, 1.0) },
            }, _state, sink, () => _clock.Now);
            g.Evaluate(Set("RateSetpoint", 8.5));
            g.Evaluate("garbage");
            var lines = File.ReadAllLines(path);
            Assert.Equal(2, lines.Length);
            Assert.Contains("ACCEPTED", lines[0]);
            Assert.Contains("SCHEMA_INVALID", lines[1]);
        }
        finally { if (File.Exists(path)) File.Delete(path); }
    }
}
