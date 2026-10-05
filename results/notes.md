# Notes

Deviations, failures and anything a reader should know. Every figure here comes from a run recorded in this repository.

## Gate runs

The gate unit tests also ran on a hosted runner (run 37375097256, commit 05615c8): 61 passed of 61. The tests and the scripted proposals first ran in a development container with 4 CPUs (Intel Xeon at 2.80 GHz), 15 GB memory and no swap. It is not a runner, and its numbers are labelled as such wherever they appear. They need no model and no download.

## Models

- Original models, from `ollama list` on the original machine: llama3:latest (365c0bd3c000), mistral:latest (f974a74358d6), tinyllama:latest (2644915ede35), mxbai-embed-large:latest (468836162de7), all-minilm:latest (1b226e2802db).
- E1 is a full grid of two implementations by three models (`PROTOCOL.md` section 6, E1).
- Tag resolution, from run 37375097339 (`results/run-37375097339-manual-models-budget/models_resolve.csv`): `llama3:latest`, `tinyllama:latest`, `mxbai-embed-large:latest` and `all-minilm:latest` resolve to the original ids. `mistral:latest` resolves to `6577803aa9a0`, not to `f974a74358d6`. The tag now names the same model as `mistral:7b`, so the original `mistral:latest` is not available under that tag. We listed the 84 tags of the `mistral` library (the `tags` job of runs 37379679812 and 37380524685) and computed each tag's id from its manifest. A self-check on `latest` and `7b` gave `6577803aa9a0` as expected. No tag carries `f974a74358d6`. The original model cannot be pulled, so the mistral cells run today's `mistral:latest` and are labelled so.
- Embedding dimensions measured in the same run: `mxbai-embed-large` 1024, `all-minilm` 384. B declares its collection with 1536.

## Manual

Candidates and the verification record are in `docs/manual_candidates.md`. The Fulton Endura XE manual is adopted provisionally: 132 pages, civilian, several capacities, four passages that limit a statement to some variants. `manuals/chosen.txt` names it.

## Gate observations

We did not change the gate code. We noticed three behaviours.

1. `MaxCumulativeChangePerWindow` is a single number applied to every tag, whatever its units. A bound sized for a small-unit tag refuses a large-unit tag. Test: `Cumulative_bound_is_one_number_for_all_tags_regardless_of_units`.
2. `Check` evaluates the rate limit before the cumulative limit. An action exactly one window old still counts, because the cut-off removes only entries strictly older than `now - window`.
3. The unknown-kind branch of `Check` is reachable only with a typed proposal. The JSON deserializer rejects unknown kinds first.

Scripted proposals:

- The harness `gate/scripted/` reads `gate/proposals/scripted.json`. It does not modify the gate.
- Scenarios that must accept pressure steps use an envelope with no cumulative bound and a high action limit. The envelope in `Program.cs` has a cumulative bound of 1.5, which refuses any pressure step above 1.5 (observation 1).
- Markdown code fences around otherwise valid JSON are refused as SCHEMA_INVALID (case X09). E3 step 3 will show how often model output carries them.

## Default context windows and silent truncation

Ollama cuts a prompt that exceeds the context window and says nothing. We measured what the models see. Two checks, one table each. Both ran on hosted runners with 4 CPUs and 15 GB, on pages of the Fulton manual (`results/run-37380524685-truncation-checks/` and `results/run-37379679812-truncation-checks/`).

The window in effect, as `/api/ps` reports it for default settings: llama3 4096, mistral 4096, tinyllama 2048, all-minilm 256, mxbai-embed-large 512.

### Check 1: prompts sent to the chat models

The prompt is built as the pipelines build it. B uses the first 1, 2, 3, 5 or 8 text-rich whole pages after the first quarter of the manual, A uses three chunks of 1000 characters. Tokens used is the `prompt_eval_count` with the default window. Tokens offered is the count of the same prompt without a cut. Ollama limits `num_ctx` to the length a model was trained with (8192 for llama3, 2048 for tinyllama), so for llama3 and tinyllama we counted the offered tokens piece by piece. The two methods differ by at most 8 tokens where a prompt fits. For mistral a single pass with a window of 32768 held every prompt.

| Model | Window in effect | Prompt | Characters | Tokens offered | Tokens used | Dropped |
|---|---|---|---|---|---|---|
| llama3 | 4096 | A, 3 chunks | 3,288 | 687 | 692 | none |
| llama3 | 4096 | B, 1 page | 3,554 | 896 | 896 | none |
| llama3 | 4096 | B, 2 pages | 6,719 | 1560 | 1560 | none |
| llama3 | 4096 | B, 3 pages | 10,943 | 2482 | 2482 | none |
| llama3 | 4096 | B, 5 pages | 16,527 | 3603 | 3603 | none |
| llama3 | 4096 | B, 8 pages | 27,394 | 6008 | **2060 of 6008** | 3948 |
| mistral | 4096 | A, 3 chunks | 3,288 | 796 | 798 | none |
| mistral | 4096 | B, 1 page | 3,554 | 1032 | 1032 | none |
| mistral | 4096 | B, 2 pages | 6,719 | 1844 | 1844 | none |
| mistral | 4096 | B, 3 pages | 10,943 | 2907 | 2907 | none |
| mistral | 4096 | B, 5 pages | 16,527 | 4159 | **2051 of 4159** | 2108 |
| mistral | 4096 | B, 8 pages | 27,394 | 6914 | **2051 of 6914** | 4863 |
| tinyllama | 2048 | A, 3 chunks | 3,288 | 862 | 854 | none |
| tinyllama | 2048 | B, 1 page | 3,554 | 1102 | 1102 | none |
| tinyllama | 2048 | B, 2 pages | 6,719 | 1954 | 1952 | none |
| tinyllama | 2048 | B, 3 pages | 10,943 | 3090 | **1026 of 3090** | 2064 |
| tinyllama | 2048 | B, 5 pages | 16,527 | 4405 | **1026 of 4405** | 3379 |
| tinyllama | 2048 | B, 8 pages | 27,394 | 7288 | **1026 of 7288** | 6262 |

What the table shows:

- When a prompt exceeds the window, the model sees about half of the window and the rest is lost. The tokens used were 2060 of 4096 for llama3, 2051 of 4096 for mistral and 1026 of 2048 for tinyllama.
- On this sample, B's five-page prompt fits in llama3 (3603 of 4096 tokens), is cut for mistral (4159 offered) and is cut for tinyllama from three pages on. The default prompt of A, three chunks, fits in every model.
- The pages of the Fulton manual hold 4,506 characters on average (594,808 over 132 pages). The five pages in this sample hold 16,527 characters. Five pages of the average size would hold about 22,530 characters, so llama3 may cut B's prompt as well. E1 records the counts per question.
- The counts of E1 are those of the default window. A raised window is an E2 factor.

### Check 2: text sent to the embedding models

We embedded 20 pages spread over the manual (median 2,390 characters, median 617 tokens) with Ollama's default behaviour, and embedded the longest prefix of each page that fits the window with truncation switched off. Tokens offered are the sum of the token counts of consecutive pieces that each fit the window.

| Model | Window | Pages cut | Median tokens offered | Median tokens used | Cosine, full page against page cut to the window (median, lowest) | Cosine, full page against the text that was dropped (median) |
|---|---|---|---|---|---|---|
| all-minilm | 256 | 20 of 20 | 617 | 256 | 0.999866, 0.988759 | 0.616611 |
| mxbai-embed-large | 512 | 13 of 20 | 617 | 512 | 1.0, 0.93246 | 0.788456 |

- Both models drop the text beyond the window without a message. The embedding of a full page is practically the embedding of its beginning.
- B embeds whole pages with all-minilm, so a page is represented by its first 256 tokens. Every sampled page was longer than that.
- A's chunks hold about 1000 characters and fit the window of mxbai-embed-large.
- The lowest cosines are probably the word-boundary cut being a few tokens shorter than the window. We have not checked that.

## Budget measurements

Source: `results/run-37375097339-manual-models-budget/budget_calls.csv`. Prompts built from AERCO pages 37, 40, 43, 44 and 45. A_like is three chunks of 1000 characters (3,140 characters in the prompt). B_like is five whole pages (16,590 characters). Each prompt was sent twice. The first call is the one that matters, because the second reuses the prompt cache. `num_predict` was capped at 256, and a call that reached the cap is marked. Hardware: 4 CPUs, 15 GB, CPU only.

| Model | Shape | Prompt tokens | Prompt processing (derived tokens/s) | Generated tokens | Generation (derived tokens/s) | Wall time, first call |
|---|---|---|---|---|---|---|
| llama3:latest | A_like | 743 | 20.16 | 108 | 7.01 | 52.3 s |
| llama3:latest | B_like | 3550 | 18.93 | 91 | 4.51 | 207.8 s |
| mistral:latest | A_like | 900 | 22.94 | 80 | 6.71 | 51.2 s |
| mistral:latest | B_like | 2051 | 21.85 | 194 | 5.40 | 129.8 s |
| tinyllama:latest | A_like | 948 | 133.07 | 256 (cap) | 39.09 | 13.7 s |
| tinyllama:latest | B_like | 1026 | 129.31 | 256 (cap) | 38.68 | 14.6 s |

The wall time of the first call is the time per question we budget with. In E1 every question retrieves different text, so the prompt cache does not help.

Sizing of E1 for 40 questions and 3 repeats, 120 question runs per cell. This is arithmetic on the wall times above and not a measurement. It assumes the probe's wall time holds for real questions. The probe capped A's answers at 256 tokens, and A's default allows 2000, so A's times are a lower bound. The probe text was the AERCO manual and not the Fulton manual.

| Cell | Seconds per question | Hours for 120 runs | Minutes per repeat of 40 |
|---|---|---|---|
| A-llama3 | 52.3 | 1.74 | 34.9 |
| A-mistral | 51.2 | 1.71 | 34.1 |
| A-tinyllama | 13.7 | 0.46 | 9.1 |
| B-llama3 | 207.8 | 6.93 | 138.5 |
| B-mistral | 129.8 | 4.33 | 86.6 |
| B-tinyllama | 14.6 | 0.49 | 9.7 |
| Total | | 15.65 | |

The six cells fit. They do not fit in one job, because B-llama3 alone needs 6.93 hours and a hosted job is limited to six hours. The proposed run order is one job per cell and repeat, 18 jobs of at most 2.31 hours each. Repeat 1 of all six cells goes first, so that a complete grid exists after one pass, and repeats 2 and 3 follow. Within a pass the order does not matter when the jobs run in parallel.

Actions minutes: the Actions API reported 0 billable milliseconds for run 37375097339, which took 15 minutes 31 seconds on the runner. The repository is public. The runner time of E1 is about 939 minutes by the arithmetic above, spread over 18 jobs.

E2 model: `llama3:latest`. Its tag resolves to the original id, which mistral's does not. Its default window of 4096 held B's five-page prompt on the AERCO text, while mistral's and tinyllama's counts suggest truncation. E2 has fourteen cells, including E2g (context window raised to 8192), the two brackets E2h (no retrieval) and E2i (oracle retrieval) and E2j (extraction repaired). With llama3 at B's measured time, 3 repeats of 40 questions take 97.0 hours of runner time (32.3 hours for one repeat), again as 42 jobs of about 2.3 hours. E2e uses the other two models for its small and large cells.

Larger runners: we measured one runner size only, so we cannot state a speed-up. Runner minutes are not the limit for a public repository. The limits are the six hours per job and the number of jobs that run at once, and splitting by cell and repeat addresses both. A larger runner would shorten each job only if generation and prompt processing scale with cores, which we have not measured.

## Determinism

With temperature 0 and seed 42, repeat 1 and repeat 2 of the same prompt gave the same number of generated tokens in five of the six pairs. The mistral B_like pair gave 194 and 256 tokens (the second reached the cap). Repeat 2 reuses the prompt cache in every pair. The cause is not established. The model answers are in the workflow artifact, and the two answers have not been compared yet.

## Which experiment tests which claim

Claim wording is taken from `PROTOCOL.md`. A claim that misstates the article is to be corrected there.

| Claim | Tested by | Where to read it |
|---|---|---|
| The reproduction shows the pattern of the original three examples: A gives a procedure for an excluded variant, B declines | E1, applicability category, A versus B in each model column | summary E1 table, per-question outcomes |
| Returning a procedure for an excluded variant is the central failure case | E1 applicability category; retrieval of the chunk that holds the exclusion | retrieval.csv, answers.csv |
| Prompt and model size were confounded in the original | E1 full grid (both implementations with each model); E2b with E2e | summary E1 and E2 tables |
| Chunking may matter more than model choice | E2a compared with E2e | summary E2 tables |
| Generation settings (line-break stop, shortest answer) change correctness or completeness | E2c | summary E2 tables |
| Retrieval with no relevance threshold forces an answer from unrelated text | E2d, unanswerable category | summary E2 tables |
| A prompt cut to half the window changes answers | E2g compared with the base cell; prompt truncation table | summary E2 tables |
| Query rewriting changes retrieval from the second turn onward | E2f | summary E2 tables |
| Declaring 1536 dimensions for 384-dimension embeddings does not break B | E1 B retrieval hit rate; measured embedding dimensions recorded by the `manual-models-budget` workflow | retrieval.csv |
| Documentation placed in the prompt hits the default context window | E5 | `prompt_eval_count` and truncation flags |
| A deterministic gate refuses out-of-envelope actions that a model proposes, including trip inhibition | E3 step 2 (scripted), step 3 (model-generated), step 4 (adversarial; the count of accepted out-of-envelope actions is reported) | gate.csv, summary E3 |
| Small models run on edge-class hardware at usable speed | E4, plus the setup and budget probes, labelled as runner measurements (4 CPUs, not the original device) | resources.csv |

## Known open issue: intermittent failure in the stub-based .NET tests

In full runs of the Python test suite, one .NET test fails now and then with `System.Net.Http.HttpIOException: The response ended prematurely` while talking to `tools/stub_ollama.py`. We have seen it in about 4 of roughly 25 full runs, in different tests each time (`tests/test_pipeline_b.py::test_answers_carry_token_counts_and_context`, `tests/test_pipeline_b.py::test_prompt_stop_and_determinism`, `tests/test_gate_modelrun.py::test_counts_for_the_operator_requests`). Each of these passes when run alone, and a loop of one test passed 12 of 12. A loop of the two .NET test modules failed 3 of 10 runs, so the trigger is a sequence of runs and not one test. The cause is not established. The stub answers over HTTP/1.0 and closes the connection after each reply, and the .NET client may be reusing a connection the stub has just closed. We have not tested that. The failure affects only the stub and the tests. No result in this repository depends on the stub, and no workflow runs the Python tests.


## Primary manual: pages with garbled text

The primary manual (Cummins fire pump drive engine CFP11E, Doc. A042J562 Rev. 1, SHA-256 `a6a8ea25b6ea6e3b…`, 155 pages) has fonts without a Unicode map on some pages. `pdftotext`, `pypdf` and PdfPig all return glyph codes instead of letters on these pages. The codes are shifted by a constant, and a page counts as garbled when it reads as English only after the shift is undone. That gives 9 pages: 4, 5, 96 to 101 (the first troubleshooting charts) and 115. Pages 112 and 86 have a few garbled figure labels but their text is readable. An earlier version of this note counted 26 pages. It counted pages with few common English words, which included readable tables, fault code charts (pages 102 to 110), wiring text (151 to 155) and drawing legends. That count was wrong and is withdrawn. Pages 117 to 149 hold drawings without text.

Decision of the maintainer: the baseline does not repair the text, because the original builds did nothing special at extraction. We record the effect. E1 stores, for every cell and repeat, the number of chunks and vectors, the number of garbled chunks and how often a garbled chunk appears in the retrieved set (`garbled.json`). No question depends on a garbled page. Extraction repaired by the constant-shift decode is a low-priority E2 factor.
