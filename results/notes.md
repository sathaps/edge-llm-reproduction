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


## Check 3: Ollama 0.3.14 (the period of the original builds) against 0.35.1

The original builds date from about October 2024, when Ollama was at 0.3.x. Run 37387498181 (`ollama-period`, commit 93573ef) installed 0.3.14 on a runner and repeated the legacy-endpoint probe and the embedding truncation check. The original machine now runs a current release, so the original version cannot be recovered. This is the nearest release of the period.

Legacy `/api/embeddings` with input longer than the window (inputs of 50 to 2000 short words):

| Ollama | Input of 150 words or more for all-minilm (window 256), 200 words or more for mxbai-embed-large (window 512) |
|---|---|
| 0.3.14 | HTTP 200 for every length up to 2000 words. The input is cut to the window without a message |
| 0.35.1 | HTTP 500, "the input length exceeds the context length" (local probe; the runner probe of `check_legacy_embed.py` is part of run 37386511987) |

So B's original behaviour with page-level chunks was a silent cut at the embedding window. The 0.35.1 behaviour is an error, and B runs through `/api/embed` here (`embedding_endpoint`, see `config/README.md`), which cuts silently in both releases. `/api/embed` returned the same token counts on both releases: 256 for all-minilm and 512 for mxbai-embed-large from 200 words up.

Embedding truncation on 20 sampled pages (full page against the longest prefix that fits the window):

| Model | Release | Window | Pages cut | Median tokens offered, used | Cosine full vs prefix, median / min | Cosine full vs tail |
|---|---|---|---|---|---|---|
| all-minilm | 0.35.1 (run 37380524685) | 256 | 20 of 20 | 617, 256 | 0.999866 / 0.988759 | 0.6166 |
| all-minilm | 0.3.14 (run 37387498181) | 256 (assumed) | 20 of 20 | 615, 256 | 0.995022 / 0.785729 | 0.531946 |
| mxbai-embed-large | 0.35.1 | 512 | 13 of 20 | n/a, 512 | 1.0 / 0.93246 | 0.7885 |
| mxbai-embed-large | 0.3.14 | 512 (assumed) | 13 of 20 | 615, 512 | 1.0 / 0.77694 | 0.797955 |

The cut counts are the same. The vectors differ slightly between releases: with 0.3.14 the full page and its prefix are less alike (median 0.995 against 0.9999 for all-minilm, minimum 0.79 against 0.99). The pages sampled in the two runs come from the same manual with the same rule, but the check does not control for the difference in tokenization or normalization between the releases, so we report the difference and do not explain it.


## Retrieval consequence of the embedding window

Run 37386511987 (commit 2ed114f, Ollama 0.35.1, Fulton manual). Each page has one vector, as in B. A page is cut into passages of three sentences. A passage is inside when it lies wholly within the longest prefix of its page that fits the window, and beyond when it starts after that prefix. Each passage is queried with its own first sentence, and a query is a hit when its page is among the five nearest page vectors. Up to 150 passages per group, drawn with seed 42, from pages longer than the window. Queries whose sentence also occurs on another page are left out.

| Model | Window | Pages longer than the window | Group | Queries | Page in top 5 | Page first |
|---|---|---|---|---|---|---|
| all-minilm | 256 | 109 | inside | 150 | 107 of 150 | 83 of 150 |
| all-minilm | 256 | 109 | beyond | 150 | 53 of 150 | 16 of 150 |
| mxbai-embed-large | 512 | 72 | inside | 150 | 103 of 150 | 67 of 150 |
| mxbai-embed-large | 512 | 72 | beyond | 141 | 61 of 141 | 22 of 141 |

B uses all-minilm, so a passage that lies beyond the first 256 tokens of its page is found in the top 5 in 53 of 150 queries, against 107 of 150 for a passage inside the window, and in the first place in 16 of 150 against 83 of 150. A passage beyond the window is still found about a third of the time, because the page vector holds the beginning of the page and neighbouring text shares words. The result comes from the Fulton manual. The job failed on the Cummins manual (run 37389480081) because pages without text give an empty input, which the script now skips.


## Verification of the Cummins questions (2026-10-05)

The maintainer verified all 45 rows of the v2 pack (29 ok, 16 fix, no drop). He wrote each fix in the correction column and did not edit the question or answer cells. `scripts/merge_verification.py` reads a non-empty correction as the change: an optional `Question:` line replaces the question, `Answer:` up to the `PDF page(s) N.` marker replaces the reference answer, the marker sets the source pages and what follows it is his note to us. `docs/verification_merge_v2.md` lists question, source pages, required elements and forbidden elements before and after for the 16 rows. Required elements were then derived from the corrected answers: an element for every prerequisite or step he added, and none removed unless his answer removed the fact.

Notes on three rows:

1. sc-02, weekly battery maintenance. Page 79 (weekly section) says to replace the battery when the specific gravity is below 1.215. Page 101 (low battery voltage chart) says to charge the battery below 1.215. The manual is inconsistent on this. The question is tied to the weekly section, and the reference answer keeps the weekly-section wording.
2. un-06, oil capacity of a CFP23E. The maintainer reads the data on page 112 as labelled CFP11E in the PDF. Our extraction of the page shows no model name in the table text. The label is in a garbled figure label: the raw text of the cooling loop chart title on page 112 decodes with the constant shift to "CFP11E Cooling Loop", followed by "Raw Water Flow [GPM]" and "Raw Water Temperature [F]". A reader sees the label on the chart. It is absent from the extracted text of the table, and no pipeline can retrieve it as a model name for the table. The question stays unanswerable.
3. ap-01. The reference answer now gives only the CFP60E value (345 kPa, 50 psi). The forbidden elements are the other models' value (276 kPa, 40 psi). The automatic scorer fails a correct answer that mentions 40 psi for the other models as a contrast. The scorer is an addition to the maintainer's blind marks, and his mark is the one reported.

## E1 repeat 1: commits, software and the rule for reruns

The frozen files are tagged `protocol-v1` at commit 07f4a33 (question set, scorer, marking rules, planned comparisons, E1 cells and pipeline settings; `protocol-v1.manifest` lists their SHA-256).

E1 repeat 1 ran in two parts. Run 37394227689 ran five cells (A-tinyllama, B-tinyllama, A-llama3, B-llama3, B-mistral) from commit 62e8c3d. The A-mistral job of that run failed before any model work, because the Ollama installer returned before its server answered and the first pull found no server. A-mistral was rerun alone from commit b41cea7.

The difference between 62e8c3d and b41cea7 is limited to the workflow: `.github/workflows/e1.yml` (the server is started explicitly when the installer's service is slow, pulls are retried, named cells can be rerun) and `experiments/e1_request.json` (the request itself). No pipeline, config, question, scorer, marking-rule, script or experiment-cell file differs. Checks on both commits: `scripts/freeze_manifest.py check protocol-v1.manifest` prints "frozen files unchanged" on 62e8c3d and on b41cea7; the combined SHA-256 over the files under `pipelines/`, `config/`, `questions/`, `scoring/` and `scripts/` and over `experiments/e1.json` and `experiments/comparisons.json` is `ac92f96e8ce585dabea738d0bba2d8d7856d6fe126f56e1a1f30762720b68f64` on both. Commits after b41cea7 add `.github/workflows/collect.yml` (copies finished runs' files into the repository) and `scripts/e1_table.py`; they change no pipeline, config, question, scorer or marking file.

The E1 table lists for every cell its commit, Ollama version, model digest and embedding digest (`scripts/e1_table.py`, from the `run.json` of each cell). A cell that ran on a different Ollama version or a different model digest from the others of its model is reported as different, and it is not used until the maintainer has seen the difference.

Rule for every rerun after the freeze: workflow fixes are allowed. Anything that changes pipeline behaviour (pipeline code, config, prompts, scoring, questions, models or Ollama version) after the freeze is a recorded deviation that the maintainer sees before the result is used.

## Which part of an over-long prompt the model sees (probe)

Run 37391090572, jobs `survival (llama3:latest)`, `survival (mistral:latest)`, `survival (tinyllama:latest)`, commit edde00b, Ollama 0.35.1, default window. The prompt has B's template and eight generated filler pages, 16 code words at page starts and ends, one in the question. Each code word is asked for with a separate question: which code word follows the label. A label that is not in the prompt is the negative control. All 17 labels are in the prompt as sent.

| Model | Window | Tokens used | Codes read correctly (of 17) | Which ones | Control |
|---|---|---|---|---|---|
| llama3 | 4096 | 2060 | 6 | page 6 end, pages 7 and 8, question | answered none |
| mistral | 4096 | 2051 | 4 | page 7 end, page 8, question | answered none |
| tinyllama | 2048 | 1026 | 0 | none | gave a code word |

Every code word from the head of the prompt to page 6 (llama3) or page 7 (mistral) was lost, although it was sent. The model reads the end of the prompt and does not read the start. mistral answered none for four of the lost codes, llama3 gave a wrong code word for all of them. tinyllama read no code and also failed the control, so its answers carry no information. The model listing of codes (first step of the same job) is in the job logs and in `survival_<model>.csv`; we do not use it, because a model that lists codes can miss a code it was shown.

Run 37389480081 used the same logic. Its retrieval job failed on pages without text, so we do not use it.

## Embedding retrieval on the Cummins manual

Run 37391090572, job `retrieval`, commit edde00b, Ollama 0.35.1, `/api/embed`. Passages of three sentences, queried with their own first sentence. A hit means the right page is among the 5 nearest page vectors. "Inside" passages lie within the part of the page that fits the window, "beyond" passages start after it. Only pages longer than the window take part.

| Model | Window | Pages longer than window | Group | Queries | Top 5 | Top 1 |
|---|---|---|---|---|---|---|
| all-minilm | 256 | 91 | inside | 150 | 134 (89.3 %) | 105 (70.0 %) |
| all-minilm | 256 | 91 | beyond | 150 | 40 (26.7 %) | 19 (12.7 %) |
| mxbai-embed-large | 512 | 36 | inside | 135 | 100 (74.1 %) | 70 (51.9 %) |
| mxbai-embed-large | 512 | 36 | beyond | 46 | 7 (15.2 %) | 3 (6.5 %) |

Text beyond the window is found far less often. The same job repeats the endpoint check on this manual: the legacy `/api/embeddings` returns HTTP 500 for 600 words or more (all-minilm) and 200 words or more (mxbai) under 0.35.1, `/api/embed` returns 200 and counts 256 or 512 tokens.

## Check 3 addition: llama3 prompt truncation on Ollama 0.3.14

Run 37387498181, job `chat`, commit 93573ef, Ollama 0.3.14, `llama3:latest`, assumed window 2048 (0.3.14 does not report it, `WINDOW_ASSUMED`). The default pass and the raised pass use the same window, so the tokens used are the same.

| Shape | Units | Tokens offered | Tokens used | Tokens dropped | Truncated |
|---|---|---|---|---|---|
| A | 3 | 687 | 692 | 0 | no |
| B | 1 | 896 | 896 | 0 | no |
| B | 2 | 1560 | 1560 | 0 | no |
| B | 3 | 2482 | 1036 | 1446 | yes |
| B | 5 | 3603 | 1036 | 2567 | yes |
| B | 8 | 6008 | 1036 | 4972 | yes |

On 0.3.14 the llama3 prompt is also cut to 1036 tokens, about half of the 2048 window, as on 0.35.1 with the 4096 window (2060 used). The window default differs between the two versions (2048 assumed here, 4096 on 0.35.1) and the cut is the same fraction. We did not read the window from the server on 0.3.14.

## Where the cut falls: tail of the prompt sent alone

Run 37400903836 (`survival-tail`), commit 19b6f64, Ollama 0.35.1, default window 4096. B's template with eight generated pages and 40 numbered codes, one question per code. The tail is the prompt text from a code's label to the end, sent alone with the same window.

| Model | Tokens used by the full prompt | First code read | Tail from the first code read | Last code not read | Tail from the last code not read | Codes read (of 40) |
|---|---|---|---|---|---|---|
| llama3 | 2060 | 28 | 1991 | 27 | 2153 | 11 |
| mistral | 2051 | 31 | 1854 | 30 | 2057 | 9 |

For both models the tokens used by the full prompt lie between the two tail counts. The tail from the first code read is smaller than the tokens used (llama3 by 69, mistral by 197) and the tail from the last code not read is larger (llama3 by 93, mistral by 6). The codes are about 160 tokens apart, so the cut falls between the two labels, as the model's answers say. The counts match.

llama3 did not read code 39, the last one before the question, and mistral read it. We do not use the answer to a single code as evidence of where the cut falls.

A's shape, one system message and one user message that starts with the question followed by the pages:

| Model | Code in the system message | Code at the start of the user message |
|---|---|---|
| llama3 | read | not read |
| mistral | not read | not read |

llama3 keeps the system message and loses the start of the user message. mistral loses both. In B the instruction is the start of the single user message and is cut first. In A the question is at the start of the user message and can be cut when the message is long.

## E1 repeat 1: sanity gate, first pass (03:25 UTC, four of six cells)

Run 37394227689 (five cells, commit 62e8c3d) and run 37395147521 (A-mistral rerun, commit b41cea7), collected into `results/e1/`. `scripts/e1_gate.py` checks that each cell has 40 answers in the order of the question file, that no answer is an error, a timeout or an HTTP error recorded as text, that tokens offered, tokens used, the truncation flag and the window are present for every question, that retrieval rows exist for every question, and that `run.json` names the commit, the Ollama version and the model digest. It reads no marks and judges no answer for accuracy. The unreadable-page questions are not part of this gate. They run separately.

| Cell | Answers | Empty answers | Questions with a cut prompt (of 40) | Gate |
|---|---|---|---|---|
| A-llama3 | 40 | 0 | 0 | pass |
| A-mistral | 40 | 0 | 0 | pass |
| A-tinyllama | 40 | 0 | 2 | pass |
| B-tinyllama | 40 | 0 | 32 | pass |
| B-llama3 | not finished | | | |
| B-mistral | not finished | | | |

Software table of the four cells: Ollama 0.35.1 in every cell, the manual file has the same SHA-256 in every cell (a6a8ea25b6ea), tinyllama has the same digest in A and B (2644915ede35), the embedding digests are those of mxbai-embed-large in A (468836162de7) and all-minilm in B (1b226e2802db). A-mistral ran from commit b41cea7 and the other cells from 62e8c3d; the Ollama version, the PDF and the model digests agree where a model appears twice. mistral appears once so far, so its digest is compared when B-mistral is collected.

## Launch of the remaining experiments (04:25 UTC)

At 04:21 UTC B-llama3 and B-mistral of E1 repeat 1 (run 37394227689, started 00:29) had not finished. The four finished cells (A-llama3, A-mistral, A-tinyllama, B-tinyllama) pass the gate, and both pipelines and all three models are covered by them. A hosted job stops after 6 hours, so we also started repeat 1 of the two long B cells as shards (Amendment 7). If the first jobs finish, they are the runs of record for repeat 1 and the shards stay as a check. If they stop at the limit, the sharded runs replace them and the E1 table says so. The marking sheet is built when a complete repeat 1 of all six cells exists.

| Run id | Workflow | What | Commit |
|---|---|---|---|
| 37413607526 | e1 | repeat 1 of B-llama3 (4 shards) and B-mistral (2 shards) | 467830b |
| 37413620660 | e1 | repeats 2 and 3 of the six cells | 7aa29b2 |
| 37413633953 | e1-unreadable | the five unreadable-page questions, six cells, three repeats, automatic scorer only | d9e1f5a |
| 37413646438 | e3 | model-generated and adversarial proposals, three models | 2ec946a |
| 37413659604 | e2 | all 15 E2 cells including E2k, three repeats | 6bc6729 |

## E1 repeats 1 to 3: collection, gate and software (10:15 UTC)

Collected into `results/e1/`: run 37394227689 (repeat 1, five cells, commit 62e8c3d), run 37395147521 (A-mistral repeat 1, commit b41cea7), run 37413607526 (repeat 1 of B-llama3 as 4 shards and B-mistral as 2 shards, commit 467830b, kept as a check), run 37413620660 (repeats 2 and 3, commit 7aa29b2). The first jobs of B-llama3 and B-mistral finished within the job limit, so they are the runs of record for repeat 1.

Sanity gate (`scripts/e1_gate.py`), repeats 1, 2 and 3: every cell has 40 answers in the order of the question file, no answer is an error recorded as text, tokens offered, tokens used, the truncation flag and the window are present for every question, retrieval rows exist for every question, and `run.json` names the commit, the Ollama version and the model digest. The gate passes for all six cells in all three repeats.

Questions with a cut prompt, of 40, the same in repeats 1, 2 and 3: A-llama3 0, A-mistral 0, A-tinyllama 2, B-llama3 4, B-mistral 5, B-tinyllama 32. Empty answers: 0 in every cell.

Software (`scripts/e1_table.py`): Ollama 0.35.1 in every cell of every repeat. The manual file has the same SHA-256 in every cell. The model digests are the same wherever a model appears more than once: llama3 365c0bd3c000, mistral 6577803aa9a0, tinyllama 2644915ede35. The embedding digests are 468836162de7 (mxbai-embed-large, A) and 1b226e2802db (all-minilm, B). The A-mistral rerun from commit b41cea7 has the same Ollama version and the same mistral digest as B-mistral, which ran from commit 62e8c3d.

### Repeat-to-repeat and shard differences

Temperature is 0 and the seed 42 in every run, and answers are still not always identical. After whitespace is collapsed, the number of questions of 40 whose answer is identical in repeats 1, 2 and 3: A-llama3 13, B-llama3 37, B-tinyllama 27. Repeat 1 of B-llama3 as shards against the unsharded run: 38 of 40 identical answers, retrieval identical for 40 of 40. B-mistral: 34 of 40, retrieval identical for 40 of 40. The counts are from `results/e1/`; no mark is involved. We report E1 per repeat and do not treat a single run as the answer a model always gives.

### Marking sheet

Built from repeat 1 of the six cells (unsharded runs of record), seed 4242, in the private repository under `verification/`: 237 distinct answers of 240 (three identical answers merged). Per category: self_contained 48, condition_dependent 45, applicability 48, unanswerable 48, table_lookup 48. One tab, 40 questions. Key file SHA-256, recorded before marking: `a9801bfe50c5f961da2170e68e1a7aa27866ad94c9e8ac645f48068e8886136c`. The second-marker sample has 60 answers: 12 per category and 10 per cell, seed 7. The check script accepts a filled copy of the real sheet and of the sample, and refuses a copy with an empty cell or a value outside the lists, naming the rows. No sheet cell names a model, a cell, a run or a retrieved page.
