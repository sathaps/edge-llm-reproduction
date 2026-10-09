# Results summary

Every figure comes from a run recorded in this repository. No figure is estimated. Counts are n of N.

Status: E1 repeats 1 to 3 are collected and pass the sanity gate. The maintainer's marks of E1 repeat 1 are in; repeats 2 and 3 are not marked. E3 steps 3 and 4 are done. The unreadable-page run is scored by the automatic scorer only. E2 is collected in `results/e2/` (all 15 cells in all three repeats) and passes the sanity gate; no E2 answer is marked, and E2 appears only through the automatic scorer in P4 to P17. E4 and E5 have no results yet. The gate results below need no model.

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

## E1: collected runs and software

Source: runs 37394227689, 37395147521, 37413607526 and 37413620660, commits 62e8c3d, b41cea7, 467830b and 7aa29b2 (`results/index.md`, entry `e1-repeats-1-3`). Six cells, three repeats, 40 questions each; 720 answers. The sanity gate passes for every cell and repeat. Ollama 0.35.1 and the same manual file in every run. Questions of 40 whose prompt was cut by the default window, the same in all three repeats:

| Cell | Questions with a cut prompt (of 40) |
|---|---|
| A-llama3 | 0 |
| A-mistral | 0 |
| A-tinyllama | 2 |
| B-llama3 | 4 |
| B-mistral | 5 |
| B-tinyllama | 32 |

Answers are not always identical between repeats at temperature 0 and seed 42 (`results/notes.md`). Marks for repeat 1 follow below.

## E1 repeat 1: the maintainer's marks (blind)

Source: runs 37394227689, 37395147521 (repeat 1 of the six cells, commits 62e8c3d and b41cea7); marks by the maintainer on the blind sheet, which `scripts/marking_sheet.py check` accepted; unblinded with the key whose SHA-256 (`a9801bfe...`) was recorded before marking; computed by `scripts/e1_results.py`. Index entry `e1-rep1-marks`. 40 questions per cell, 8 per category, n of N with Wilson 95 % intervals. A mark on an answer that several cells gave counts for each of them. `unsupported_content` is not marked. One person marked; the second marker's sample is not yet marked. Files: `results/e1/marks_rep1.csv` (marks by answer id, no notes), `results/e1/marks_rep1_by_cell.csv`, `results/e1/rep1_counts.md` (all categories and fields).

| Cell | correct: yes | correct: partial | correct: no | complete: yes | abstained: yes |
|---|---|---|---|---|---|
| A-llama3 | 17 of 40 (29-58 %) | 15 of 40 (24-53 %) | 8 of 40 (10-35 %) | 20 of 40 (35-65 %) | 10 of 40 (14-40 %) |
| A-mistral | 10 of 40 (14-40 %) | 22 of 40 (40-69 %) | 8 of 40 (10-35 %) | 19 of 40 (33-63 %) | 12 of 40 (18-45 %) |
| A-tinyllama | 2 of 40 (1-17 %) | 19 of 40 (33-63 %) | 19 of 40 (33-63 %) | 6 of 40 (7-29 %) | 1 of 40 (0-13 %) |
| B-llama3 | 13 of 40 (20-48 %) | 6 of 40 (7-29 %) | 21 of 40 (37-67 %) | 13 of 40 (20-48 %) | 22 of 40 (40-69 %) |
| B-mistral | 19 of 40 (33-63 %) | 10 of 40 (14-40 %) | 11 of 40 (16-43 %) | 18 of 40 (31-60 %) | 11 of 40 (16-43 %) |
| B-tinyllama | 1 of 40 (0-13 %) | 7 of 40 (9-32 %) | 32 of 40 (65-90 %) | 5 of 40 (5-26 %) | 6 of 40 (7-29 %) |

`correct: yes` per category:

| Cell | self_contained | condition_dependent | applicability | unanswerable | table_lookup |
|---|---|---|---|---|---|
| A-llama3 | 2 of 8 (7-59 %) | 0 of 8 (0-32 %) | 7 of 8 (53-98 %) | 3 of 8 (14-69 %) | 5 of 8 (31-86 %) |
| A-mistral | 0 of 8 (0-32 %) | 0 of 8 (0-32 %) | 2 of 8 (7-59 %) | 4 of 8 (22-78 %) | 4 of 8 (22-78 %) |
| A-tinyllama | 0 of 8 (0-32 %) | 0 of 8 (0-32 %) | 0 of 8 (0-32 %) | 1 of 8 (2-47 %) | 1 of 8 (2-47 %) |
| B-llama3 | 1 of 8 (2-47 %) | 1 of 8 (2-47 %) | 1 of 8 (2-47 %) | 8 of 8 (68-100 %) | 2 of 8 (7-59 %) |
| B-mistral | 2 of 8 (7-59 %) | 1 of 8 (2-47 %) | 5 of 8 (31-86 %) | 7 of 8 (53-98 %) | 4 of 8 (22-78 %) |
| B-tinyllama | 0 of 8 (0-32 %) | 0 of 8 (0-32 %) | 0 of 8 (0-32 %) | 1 of 8 (2-47 %) | 0 of 8 (0-32 %) |

`respects_applicability: yes`, applicability questions only:

| Cell | respects_applicability: yes |
|---|---|
| A-llama3 | 7 of 8 (53-98 %) |
| A-mistral | 4 of 8 (22-78 %) |
| A-tinyllama | 0 of 8 (0-32 %) |
| B-llama3 | 1 of 8 (2-47 %) |
| B-mistral | 5 of 8 (31-86 %) |
| B-tinyllama | 1 of 8 (2-47 %) |

### Planned paired comparisons

McNemar exact on the questions both cells answered, `correct: yes` as the outcome, Holm over all 17 tests. P1 to P3 use the maintainer's marks. P4 to P16 use repeat 1 of the E2 cells with the automatic scorer only, as the plan says, because E2 answers are not marked. P17 (E2k against B-llama3, Amendment 1) was planned on marks; E2k has no marks, so P17 is computed on the automatic scorer for both cells, labelled as such, and the marked version is not computed. The last column gives the same test with partial credit counted as correct. Sources: E2 run 37413659604 (commit 6bc6729) and the E1 runs above.

| Test | Cell A | Cell B | Basis | A right | B right | Only A right | Only B right | p (McNemar exact) | p (Holm, 17 tests) | With partial credit: p / Holm |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | A-llama3 | B-llama3 | maintainer's marks | 17 | 13 | 10 | 6 | 0.454 | 1.000 | 0.011 / 0.181 |
| P2 | A-mistral | B-mistral | maintainer's marks | 10 | 19 | 2 | 11 | 0.022 | 0.382 | 0.607 / 1.000 |
| P3 | A-tinyllama | B-tinyllama | maintainer's marks | 2 | 1 | 2 | 1 | 1.000 | 1.000 | 0.015 / 0.234 |
| P4 | base | E2a-sentence-groups | automatic scorer only | 12 | 13 | 3 | 4 | 1.000 | 1.000 | 0.754 / 1.000 |
| P5 | base | E2a-procedure | automatic scorer only | 12 | 8 | 5 | 1 | 0.219 | 1.000 | 0.727 / 1.000 |
| P6 | base | E2b-supplement | automatic scorer only | 12 | 16 | 4 | 8 | 0.388 | 1.000 | 0.454 / 1.000 |
| P7 | base | E2c-no-stop | automatic scorer only | 12 | 12 | 0 | 0 | 1.000 | 1.000 | 0.062 / 0.812 |
| P8 | base | E2c-no-shortest | automatic scorer only | 12 | 10 | 2 | 0 | 0.500 | 1.000 | 0.375 / 1.000 |
| P9 | base | E2d-threshold | automatic scorer only | 12 | 12 | 2 | 2 | 1.000 | 1.000 | 0.508 / 1.000 |
| P10 | base | E2e-small | automatic scorer only | 12 | 3 | 11 | 2 | 0.022 | 0.382 | 0.031 / 0.432 |
| P11 | base | E2e-large | automatic scorer only | 12 | 13 | 7 | 8 | 1.000 | 1.000 | 0.359 / 1.000 |
| P12 | base | E2f-rewriting | automatic scorer only | 12 | 11 | 2 | 1 | 1.000 | 1.000 | 0.219 / 1.000 |
| P13 | base | E2g-window-raised | automatic scorer only | 12 | 12 | 0 | 0 | 1.000 | 1.000 | 1.000 / 1.000 |
| P14 | base | E2h-no-retrieval | automatic scorer only | 12 | 9 | 4 | 1 | 0.375 | 1.000 | 0.022 / 0.337 |
| P15 | base | E2i-oracle | automatic scorer only | 12 | 17 | 1 | 6 | 0.125 | 1.000 | 0.180 / 1.000 |
| P16 | base | E2j-extraction-repaired | automatic scorer only | 12 | 13 | 1 | 2 | 1.000 | 1.000 | 1.000 / 1.000 |
| P17 | B-llama3-auto | E2k-period-window | automatic scorer only | 12 | 9 | 4 | 1 | 0.375 | 1.000 | 0.625 / 1.000 |

With 17 tests in the Holm family no adjusted p-value falls below 0.05 when `correct: yes` is the outcome. The smallest adjusted values are 0.382 for P2 and P10.

### Agreement of the automatic scorer with the maintainer

Unit: the 237 distinct answers of repeat 1. The scorer ran without the retrieved text; `unsupported_content` is not compared.

| Field | Same mark | Same on yes versus not yes | Cohen's kappa | N |
|---|---|---|---|---|
| correct | 177 of 237 | 203 of 237 | 0.612 | 237 |
| complete | 217 of 237 | 217 of 237 | 0.804 | 237 |
| respects_applicability | 43 of 48 | 43 of 48 | 0.770 | 48 |
| abstained | 213 of 237 | 213 of 237 | 0.704 | 237 |

Scorer against maintainer for `correct` (rows scorer, columns maintainer):

| scorer \ maintainer | yes | partial | no |
|---|---|---|---|
| yes | 46 | 16 | 2 |
| partial | 6 | 47 | 10 |
| no | 10 | 16 | 84 |


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

## E2: collected runs (no accuracy)

Source: run 37413659604 (`e2`), commit 6bc6729 (`results/index.md`, entry `e2-collection`). Three repeats of 40 questions per cell, all collected. The table counts questions whose prompt was cut by the window, from recorded tokens. It is not a result on answers.

| Cell | Repeats collected | Questions with a cut prompt (of 40), repeats 1, 2, 3 |
|---|---|---|
| base | 3 of 3 | 4, 4, 4 |
| E2a-sentence-groups | 3 of 3 | 1, 1, 1 |
| E2a-procedure | 3 of 3 | 10, 10, 10 |
| E2b-supplement | 3 of 3 | 4, 4, 4 |
| E2c-no-stop | 3 of 3 | 4, 4, 4 |
| E2c-no-shortest | 3 of 3 | 4, 4, 4 |
| E2d-threshold | 3 of 3 | 0, 0, 0 |
| E2e-small | 3 of 3 | 32, 32, 32 |
| E2e-large | 3 of 3 | 5, 5, 5 |
| E2g-window-raised | 3 of 3 | 0, 0, 0 |
| E2h-no-retrieval | 3 of 3 | 0, 0, 0 |
| E2i-oracle | 3 of 3 | 0, 0, 0 |
| E2f-rewriting | 3 of 3 | 1, 1, 1 |
| E2j-extraction-repaired | 3 of 3 | 4, 4, 4 |
| E2k-period-window | 3 of 3 | 16, 16, 16 |

## E4: resource use

Source: the per-job resources files of runs 37394227689, 37395147521, 37413607526 and 37413620660 (E1, commits 62e8c3d, b41cea7, 467830b, 7aa29b2) and run 37413659604 (E2, commit 6bc6729), summarised by `scripts/e4_summary.py`. Index entry `e4-resources`. Runner measurements: GitHub-hosted runner, 4 CPUs, 15 GB, CPU only. Each cell is the mean over three repeats with the smallest and largest value in brackets. Memory is the peak resident size, sampled every 0.1 s. Cells of B on llama3 and mistral ran as shards (4 and 2 jobs per repeat): the memory is the largest peak, the time per answer is weighted by answers, the index time is the mean over shards, and the job time is the sum over shards. Several jobs ran at the same time on different runners, and the time per answer varies by a factor of two between repeats of the same cell; we report the range and draw no conclusion from small differences.

E1:

| Cell | Repeats | Jobs per repeat | Peak memory, pipeline (MB) | Peak memory, Ollama (GB) | Index build (s) | Index size (KB) | Time per answer (s) | Job time, summed over shards (h) |
|---|---|---|---|---|---|---|---|---|
| A-llama3 | 3 | 1 | 168 (168-169) | 11.1 (11.1-11.2) | 169.6 (90.3-214.4) | 226 (226-226) | 88.6 (48.5-119.5) | 1.04 (0.57-1.40) |
| A-mistral | 3 | 1 | 169 (168-169) | 11.8 (11.7-12.0) | 201.5 (174.4-216.2) | 226 (226-226) | 129.5 (115.4-139.6) | 1.51 (1.34-1.62) |
| A-tinyllama | 3 | 1 | 169 (168-169) | 2.6 (2.6-2.6) | 172.2 (89.9-213.4) | 226 (226-226) | 36.9 (22.1-44.5) | 0.47 (0.28-0.57) |
| B-llama3 | 3 | 4 | 263 (238-298) | 9.5 (7.7-13.1) | 6.2 (5.1-7.2) | 1252 (1252-1252) | 130.8 (81.6-179.9) | 1.97 (0.92-3.52) |
| B-mistral | 3 | 2 | 255 (236-290) | 11.2 (10.3-12.8) | 5.9 (4.4-7.5) | 1252 (1252-1252) | 139.4 (72.9-195.1) | 1.83 (0.82-2.51) |
| B-tinyllama | 3 | 1 | 235 (231-239) | 1.8 (1.8-1.9) | 7.3 (6.2-8.4) | 1252 (1252-1252) | 11.6 (6.0-18.0) | 0.13 (0.07-0.20) |

E2 (B on llama3 unless the cell name says otherwise):

| Cell | Repeats | Jobs per repeat | Peak memory, pipeline (MB) | Peak memory, Ollama (GB) | Index build (s) | Index size (KB) | Time per answer (s) | Job time, summed over shards (h) |
|---|---|---|---|---|---|---|---|---|
| E2a-procedure | 3 | 4 | 258 (239-286) | 7.8 (7.8-7.8) | 5.0 (4.0-5.8) | 1112 (1112-1112) | 147.2 (100.3-200.5) | 1.65 (1.13-2.24) |
| E2a-sentence-groups | 3 | 4 | 274 (236-304) | 6.5 (6.5-6.5) | 10.0 (8.4-11.1) | 1768 (1768-1768) | 73.0 (58.6-87.0) | 0.83 (0.67-0.99) |
| E2b-supplement | 3 | 4 | 253 (237-286) | 7.7 (7.6-7.7) | 7.6 (7.5-7.7) | 1252 (1252-1252) | 174.5 (147.7-193.7) | 1.96 (1.66-2.17) |
| E2c-no-shortest | 3 | 4 | 296 (282-308) | 7.7 (7.7-7.8) | 7.1 (7.1-7.1) | 1252 (1252-1252) | 159.2 (146.2-167.1) | 1.79 (1.64-1.87) |
| E2c-no-stop | 3 | 4 | 241 (233-250) | 7.7 (7.5-7.8) | 6.3 (5.9-6.7) | 1252 (1252-1252) | 138.3 (119.7-156.1) | 1.55 (1.34-1.75) |
| E2d-threshold | 3 | 4 | 258 (238-290) | 5.8 (5.8-5.8) | 6.7 (6.0-7.6) | 1252 (1252-1252) | 22.5 (16.2-27.6) | 0.27 (0.19-0.32) |
| E2e-large | 3 | 2 | 236 (233-237) | 10.3 (10.3-10.4) | 7.1 (5.9-7.9) | 1252 (1252-1252) | 168.4 (130.6-199.4) | 1.88 (1.46-2.23) |
| E2e-small | 3 | 1 | 264 (238-303) | 1.9 (1.8-1.9) | 6.7 (5.5-7.7) | 1251 (1248-1252) | 15.5 (9.8-19.6) | 0.18 (0.11-0.22) |
| E2f-rewriting | 3 | 1 | 235 (231-237) | 12.4 (12.4-12.5) | 7.3 (7.2-7.5) | 1252 (1252-1252) | 169.5 (168.8-170.3) | 2.05 (2.04-2.06) |
| E2g-window-raised | 3 | 4 | 265 (240-304) | 9.0 (8.9-9.0) | 6.4 (6.2-6.7) | 1252 (1252-1252) | 139.6 (133.5-146.3) | 1.57 (1.50-1.64) |
| E2h-no-retrieval | 3 | 4 | 280 (241-301) | 5.2 (5.1-5.2) | 7.9 (7.5-8.5) | 1252 (1252-1252) | 4.9 (4.7-5.2) | 0.07 (0.07-0.08) |
| E2i-oracle | 3 | 4 | 244 (238-253) | 6.3 (6.3-6.3) | 6.9 (6.5-7.5) | 1252 (1252-1252) | 36.3 (29.6-46.3) | 0.42 (0.34-0.53) |
| E2j-extraction-repaired | 3 | 4 | 275 (239-301) | 7.5 (7.4-7.6) | 7.0 (6.9-7.3) | 1229 (1228-1232) | 139.9 (122.5-158.0) | 1.57 (1.38-1.77) |
| E2k-period-window | 3 | 4 | 261 (238-307) | 6.7 (6.7-6.7) | 6.9 (6.2-7.3) | 1252 (1252-1252) | 113.2 (95.1-123.0) | 1.28 (1.07-1.38) |
| base | 3 | 4 | 264 (237-303) | 7.7 (7.7-7.8) | 6.8 (6.4-7.1) | 1252 (1252-1252) | 149.7 (131.2-166.0) | 1.68 (1.48-1.86) |

The index of A takes 90 to 216 s (mxbai-embed-large) and of B 4 to 11 s (all-minilm). The index file of A is 226 KB and of B about 1.2 MB. These figures describe this runner, not an industrial edge device.

## Limitations

- One manual. Every result comes from a single public manual. Findings on retrieval and applicability may not carry over to manuals with other layouts.
- One main marker. One person marks every E1 repeat-1 answer. A second person marks a random blind sample of 60 answers, and the agreement is reported as counts and Cohen's kappa. Marking is blind to configuration, but the judgement on "partial" and "complete" rests on those two people by anyone else.
- Small models on a 4-CPU runner. Model results come from models served by Ollama on a GitHub-hosted 4-CPU, 15 GB, CPU-only runner. They say nothing about larger models or other hardware. E4 figures are runner measurements, not edge-device measurements.
- A re-implementation, not the original builds. The two pipelines are rebuilt from a written description on public material. The original builds, documents and hardware are not part of this repository. No result here was measured on them.
- Small samples. Counts are n of N with small N per category. A difference of one or two questions is within what one reworded question could change.
