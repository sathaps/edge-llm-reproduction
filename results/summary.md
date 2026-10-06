# Results summary

Every figure comes from a run recorded in this repository. No figure is estimated. Counts are n of N.

Status: E1 repeats 1 to 3 are collected and pass the sanity gate. No E1 answer is marked yet, so no E1 accuracy is reported. E3 steps 3 and 4 are done. The unreadable-page run is scored by the automatic scorer only. E2 is running; its results are collected in `results/e2/` and not summarised. E4 and E5 have no results yet. The gate results below need no model.

## Runner measurements

Source: run 37375097339 (`manual-models-budget`), commit 05615c8. Index entry: `runner-measurements`.

Tag resolution, context windows, speed and the per-question time budget are in `results/notes.md`. They are timing probes and not question-set results.

## E3 steps 1 and 2: gate unit tests and scripted proposals

No model is involved. The state reader is a stand-in with fixed values. The scripted run was in a development container (4 CPUs, 15 GB, .NET SDK 8.0), not on a runner.

Source: unit tests on a runner, run 37375097256 (`gate-tests`), commit 05615c8; scripted proposals in the development container, commit 05615c8 (the files under `gate/` are the same at later commits). Index entry: `gate-e3-steps-1-2`.

| Run | Command | Result |
|---|---|---|
| Unit tests | `dotnet test` in `gate/tests` | 61 passed of 61, 0 failed, 0 skipped |
| Unit tests on a hosted runner | the `gate-tests` workflow, run 37375097256 | 61 passed of 61, 0 failed, 0 skipped |
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

## E1: collected runs and software (no accuracy)

Source: runs 37394227689, 37395147521, 37413607526 and 37413620660, commits 62e8c3d, b41cea7, 467830b and 7aa29b2 (`results/index.md`, entry `e1-repeats-1-3`). Six cells, three repeats, 40 questions each; 720 answers. The sanity gate passes for every cell and repeat. Ollama 0.35.1 and the same manual file in every run. Questions of 40 whose prompt was cut by the default window, the same in all three repeats:

| Cell | Questions with a cut prompt (of 40) |
|---|---|
| A-llama3 | 0 |
| A-mistral | 0 |
| A-tinyllama | 2 |
| B-llama3 | 4 |
| B-mistral | 5 |
| B-tinyllama | 32 |

Answers are not always identical between repeats at temperature 0 and seed 42 (`results/notes.md`). Marks by the maintainer are not yet made.

## E3 steps 3 and 4: model-generated and adversarial proposals

Source: run 37443527953 (`e3`), commit 4d4230d, Ollama 0.35.1, files in `results/e3/`. Each model received the typed action schema and the requests of `gate/proposals/requests.json` (24 operator requests) and `gate/proposals/adversarial.json` (10 requests that tell the model to ignore limits). The raw model output went to `DeterministicGate.Evaluate(string)`. The state reader is a stand-in with fixed values. The first run (37413646438) failed for mistral and tinyllama at the Ollama install and is not a result.

| Model | Requests | Parsed | Accepted | Refused | Accepted outside the envelope |
|---|---|---|---|---|---|
| llama3 | 24 operator | 23 | 10 | 14 | 0 |
| mistral | 24 operator | 23 | 9 | 15 | 0 |
| tinyllama | 24 operator | 0 | 0 | 24 | 0 |
| llama3 | 10 adversarial | 8 | 0 | 10 | 0 |
| mistral | 10 adversarial | 9 | 0 | 10 | 0 |
| tinyllama | 10 adversarial | 0 | 0 | 10 | 0 |

Refusals by reason code are in `results/e3/e3-*/requests/gate_model_summary.json` and `.../adversarial/gate_model_summary.json`. For llama3 on the operator requests: ACCEPTED 10, TRIP_INHIBIT_FORBIDDEN 5, ABOVE_HIGH_LIMIT 3, STEP_TOO_LARGE 2, and one each of BELOW_LOW_LIMIT, MODE_NOT_ALLOWED, SCHEMA_INVALID and TAG_NOT_WRITABLE. For mistral: ACCEPTED 9, TRIP_INHIBIT_FORBIDDEN 5, ABOVE_HIGH_LIMIT 2, BELOW_LOW_LIMIT 2, MODE_NOT_ALLOWED 2, STEP_TOO_LARGE 2, and one each of SCHEMA_INVALID and TAG_NOT_WRITABLE. tinyllama produced no output that parses as an action, so all 34 of its outputs were refused as SCHEMA_INVALID. No out-of-envelope action was accepted in any run. The count is what we report; with three models and 34 requests each it is not a proof that none can be.

## Unreadable-page questions (automatic scorer only)

Source: run 37413633953 (`e1-unreadable`), commit d9e1f5a, files in `results/e1_unreadable/`, scores in `results/e1_unreadable/auto_scores.csv` made with `scripts/auto_score.py`. Five questions whose source pages have no readable text, six cells, three repeats. These counts come from the automatic scorer. No person has marked them, and the scorer's `correct` is not a mark.

| Cell | Scorer: correct (of 15) | Scorer: abstained (of 15) |
|---|---|---|
| A-llama3 | 0 | 4 |
| A-mistral | 0 | 3 |
| A-tinyllama | 0 | 0 |
| B-llama3 | 0 | 12 |
| B-mistral | 0 | 7 |
| B-tinyllama | 0 | 3 |

## Limitations

- One manual. Every result comes from a single public manual. Findings on retrieval and applicability may not carry over to manuals with other layouts.
- One main marker. One person marks every E1 repeat-1 answer. A second person marks a random blind sample of 60 answers, and the agreement is reported as counts and Cohen's kappa. Marking is blind to configuration, but the judgement on "partial" and "complete" rests on those two people by anyone else.
- Small models on a 4-CPU runner. Model results come from models served by Ollama on a GitHub-hosted 4-CPU, 15 GB, CPU-only runner. They say nothing about larger models or other hardware. E4 figures are runner measurements, not edge-device measurements.
- A re-implementation, not the original builds. The two pipelines are rebuilt from a written description on public material. The original builds, documents and hardware are not part of this repository. No result here was measured on them.
- Small samples. Counts are n of N with small N per category. A difference of one or two questions is within what one reworded question could change.
