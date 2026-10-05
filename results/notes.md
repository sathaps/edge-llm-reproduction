# Notes

Deviations, failures and anything a reader should know. Every figure here comes from a run recorded in this repository.

## Gate runs

The gate unit tests and the scripted proposals ran in a development container with 4 CPUs (Intel Xeon at 2.80 GHz), 15 GB memory and no swap. It is not a runner, and its numbers are labelled as such wherever they appear. They need no model and no download.

## Models

- Original models, from `ollama list` on the original machine: llama3:latest (365c0bd3c000), mistral:latest (f974a74358d6), tinyllama:latest (2644915ede35), mxbai-embed-large:latest (468836162de7), all-minilm:latest (1b226e2802db).
- E1 is a full grid of two implementations by three models (`PROTOCOL.md` section 6, E1).
- Whether today's tags resolve to the original ids is recorded by the `manual-models-budget` workflow, whose output is copied into `results/` after it has run.

## Manual

Candidates and the verification record are in `docs/manual_candidates.md`. The verification job is `manual-models-budget`.

## Gate observations

We did not change the gate code. We noticed three behaviours.

1. `MaxCumulativeChangePerWindow` is a single number applied to every tag, whatever its units. A bound sized for a small-unit tag refuses a large-unit tag. Test: `Cumulative_bound_is_one_number_for_all_tags_regardless_of_units`.
2. `Check` evaluates the rate limit before the cumulative limit. An action exactly one window old still counts, because the cut-off removes only entries strictly older than `now - window`.
3. The unknown-kind branch of `Check` is reachable only with a typed proposal. The JSON deserializer rejects unknown kinds first.

Scripted proposals:

- The harness `gate/scripted/` reads `gate/proposals/scripted.json`. It does not modify the gate.
- Scenarios that must accept pressure steps use an envelope with no cumulative bound and a high action limit. The envelope in `Program.cs` has a cumulative bound of 1.5, which refuses any pressure step above 1.5 (observation 1).
- Markdown code fences around otherwise valid JSON are refused as SCHEMA_INVALID (case X09). E3 step 3 will show how often model output carries them.

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
| Query rewriting changes retrieval from the second turn onward | E2f | summary E2 tables |
| Declaring 1536 dimensions for 384-dimension embeddings does not break B | E1 B retrieval hit rate; measured embedding dimensions recorded by the `manual-models-budget` workflow | retrieval.csv |
| Documentation placed in the prompt hits the default context window | E5 | `prompt_eval_count` and truncation flags |
| A deterministic gate refuses out-of-envelope actions that a model proposes, including trip inhibition | E3 step 2 (scripted), step 3 (model-generated), step 4 (adversarial; the count of accepted out-of-envelope actions is reported) | gate.csv, summary E3 |
| Small models run on edge-class hardware at usable speed | E4, plus the setup and budget probes, labelled as runner measurements (2 CPUs, not the original device) | resources.csv |

## Known open issue: intermittent failure in the stub-based .NET tests

In full runs of the Python test suite, one .NET test fails now and then with `System.Net.Http.HttpIOException: The response ended prematurely` while talking to `tools/stub_ollama.py`. We have seen it in about 4 of roughly 25 full runs, in different tests each time (`tests/test_pipeline_b.py::test_answers_carry_token_counts_and_context`, `tests/test_pipeline_b.py::test_prompt_stop_and_determinism`, `tests/test_gate_modelrun.py::test_counts_for_the_operator_requests`). Each of these passes when run alone, and a loop of one test passed 12 of 12. A loop of the two .NET test modules failed 3 of 10 runs, so the trigger is a sequence of runs and not one test. The cause is not established. The stub answers over HTTP/1.0 and closes the connection after each reply, and the .NET client may be reusing a connection the stub has just closed. We have not tested that. The failure affects only the stub and the tests. No result in this repository depends on the stub, and no workflow runs the Python tests.
