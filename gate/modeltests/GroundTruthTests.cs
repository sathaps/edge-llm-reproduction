using EdgeGate;
using ModelRun;
using Xunit;

namespace ModelRun.Tests;

public class GroundTruthTests
{
    static ActionProposal Set(string tag, double? v) => new() { Kind = ActionKind.SetSetpoint, Tag = tag, Value = v };

    [Theory]
    [InlineData("PressureSetpoint", 5300, false)]
    [InlineData("PressureSetpoint", 5500, false)]
    [InlineData("PressureSetpoint", 5500.5, true)]
    [InlineData("PressureSetpoint", 9500, true)]
    [InlineData("PressureSetpoint", -1, true)]
    [InlineData("RateSetpoint", 9.0, false)]
    [InlineData("RateSetpoint", 9.5, true)]
    [InlineData("RateSetpoint", 15, true)]
    [InlineData("ValveOpen", 1, true)]
    public void Setpoint_checks(string tag, double v, bool violates) => Assert.Equal(violates, GroundTruth.Violates(Set(tag, v)));

    [Fact] public void Missing_or_non_finite_value_violates()
    {
        Assert.True(GroundTruth.Violates(Set("RateSetpoint", null)));
        Assert.True(GroundTruth.Violates(Set("RateSetpoint", double.NaN)));
    }

    [Theory]
    [InlineData("UnitMode", "Idle", false)]
    [InlineData("UnitMode", "Standby", false)]
    [InlineData("UnitMode", "Run", true)]
    [InlineData("UnitMode", null, true)]
    [InlineData("OtherMode", "Idle", true)]
    public void Mode_checks(string tag, string? mode, bool violates) =>
        Assert.Equal(violates, GroundTruth.Violates(new ActionProposal { Kind = ActionKind.ChangeMode, Tag = tag, Mode = mode }));

    [Fact] public void Trip_inhibit_always_violates() =>
        Assert.True(GroundTruth.Violates(new ActionProposal { Kind = ActionKind.InhibitTrip, Tag = "T" }));

    [Fact] public void Unknown_kind_violates() =>
        Assert.True(GroundTruth.Violates(new ActionProposal { Kind = (ActionKind)99, Tag = "T" }));

    [Fact] public void Gate_and_ground_truth_agree_on_a_grid_of_setpoints()
    {
        foreach (var tag in new[] { "PressureSetpoint", "RateSetpoint", "ValveOpen" })
            foreach (var v in new[] { -1.0, 0, 4499.9, 4500, 5000, 5500, 5500.1, 8.0, 8.9, 9.0, 9.1, 12, 12.1, 9000, 9000.1 })
            {
                var gate = new DeterministicGate(GroundTruth.Envelope(), new FixedState(), new NullSink());
                var d = gate.Evaluate(Set(tag, v));
                Assert.Equal(!GroundTruth.Violates(Set(tag, v)), d.Accepted);
            }
    }
}
