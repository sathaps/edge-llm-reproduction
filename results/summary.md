# Results summary

Every figure comes from a run recorded in this repository. No figure is estimated. Counts are n of N.

Status: no E1, E2, E4 or E5 results yet. The gate results below need no model.

## E3 steps 1 and 2: gate unit tests and scripted proposals

No model is involved. The state reader is a stand-in with fixed values. Both ran in a development container (4 CPUs, 15 GB, .NET SDK 8.0), not on a runner.

| Run | Command | Result |
|---|---|---|
| Unit tests | `dotnet test` in `gate/tests` | 61 passed of 61, 0 failed, 0 skipped |
| Scripted proposals | `dotnet run --project gate/scripted` | 57 proposals: 17 accepted, 40 refused |

Scripted proposals by reason code. Inputs: `gate/proposals/scripted.json` (the eleven proposals of `gate/src/Program.cs` in order, one recheck, and boundary cases for each rule; each scenario starts a fresh gate). Per-proposal rows: `results/gate/scripted_proposals.csv`.

| Reason code | Count |
|---|---|
| ACCEPTED | 17 |
| SCHEMA_INVALID | 12 |
| MODE_NOT_ALLOWED | 4 |
| TRIP_INHIBIT_FORBIDDEN | 4 |
| RATE_LIMIT | 3 |
| STEP_TOO_LARGE | 3 |
| TAG_NOT_WRITABLE | 3 |
| ABOVE_HIGH_LIMIT | 2 |
| CUMULATIVE_LIMIT | 2 |
| MODE_CHANGE_WHILE_RUNNING | 2 |
| VALUE_MISSING | 2 |
| BELOW_LOW_LIMIT | 1 |
| STATE_CHANGED_BEFORE_EXECUTION | 1 |
| STATE_UNAVAILABLE | 1 |
| Total | 57 |

All 57 outcomes matched the reason code the rule predicts. Every one of the 14 reason codes occurs at least once. The counts describe the coverage of the scripted set. They do not describe how often a model triggers each code. E3 step 3 measures that.

## Limitations

- One manual. Every result comes from a single public manual. Findings on retrieval and applicability may not carry over to manuals with other layouts.
- One marker. A single person marks the answers. There is no agreement figure between markers. Marking is blind to configuration, but one marker's judgement on "partial" and "complete" is not checked by anyone else.
- Small models on a 2-CPU runner. Model results come from models served by Ollama on a GitHub-hosted 2-CPU, CPU-only runner. They say nothing about larger models or other hardware. E4 figures are runner measurements, not edge-device measurements.
- A re-implementation, not the original builds. The two pipelines are rebuilt from a written description on public material. The original builds, documents and hardware are not part of this repository. No result here was measured on them.
- Small samples. Counts are n of N with small N per category. A difference of one or two questions is within what one reworded question could change.
