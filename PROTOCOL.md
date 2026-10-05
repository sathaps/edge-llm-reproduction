# Experiment protocol

This repository rebuilds two configurations of a document question-answering pipeline on a public equipment manual and measures them. The measurements support an article on language models on industrial edge devices. The original observations came from two prototype builds on an industrial field computer and were recorded as three example questions. Those builds and their documents are not published. Everything here is a re-implementation on public material, and no result was measured on the original hardware.

## 1. Rules

1. **No fabricated or estimated numbers.** Every figure in `results/` comes from a run recorded in this repository. A failed run is recorded as a failure.
2. **Public material only.** The repository contains nothing from the original builds and no non-public document, name or identifier.
3. **Verified reference answers.** A person verifies every reference answer against the manual before it is used for scoring. An unverified question is excluded from the results.
4. **Record what ran.** Every run records the commit hash, model tags and digests, the Ollama version, runner CPU count and memory, and wall-clock time.
5. **Deterministic settings.** Temperature 0 and a fixed seed. Each configuration runs three times, and all three results are reported if they differ.
6. **Negative results stay.** A result that contradicts a claim of the article is reported as measured.
7. **No secrets.** Tokens and credentials are never committed.
8. **Writing.** Committed text is plain engineering documentation in the first person plural. Sentences are short and factual.

## 2. Where it runs

GitHub Actions, on GitHub-hosted Linux runners, CPU only. Each job prints `nproc` and `free -g` at the start and saves them with the results. A job installs Ollama, pulls the models, runs the pipelines and uploads the outputs. Runner limits decide which models and how many questions fit in one job. A model has to answer one question in well under a minute for a full run of both pipelines to finish in one job.

## 3. The two configurations

Each configuration is reproduced as it was built, defaults included. The defaults are the subject of the article. `config/pipelines.json` is the single source of these settings for both pipelines.

| Dimension | Implementation A (Python) | Implementation B (.NET) |
|---|---|---|
| Base | The open-source `easy-local-rag` project (single-file local retrieval over Ollama) | A C# port of LangChain (`LangChain` NuGet packages) with its SQLite vector store |
| Embedding model | `mxbai-embed-large` | `all-minilm` |
| Chunking | Extracted text flattened, then sentences grouped into chunks of about 1,000 characters | Page-level output of the PDF loader, no text splitter |
| Retrieval depth | Top 3, no relevance threshold | Top 5, no relevance threshold |
| Grounding instruction | Tells the model to bring in relevant outside information to supplement the context | Tells the model to say it does not know when the context lacks the answer |
| Query rewriting | From the second conversational turn onward | None |
| Generation settings | Defaults | Generation stops at the first line break (`Stop = "\n"`), and the prompt asks for the shortest possible answer |
| Other | | The vector collection is declared with 1536 dimensions while `all-minilm` produces 384 |

Each default is checked against the upstream project at the pinned version. Places where upstream has changed, and details that cannot be reproduced exactly, are listed in `results/notes.md`.

### Models

| Model | Id (as printed by `ollama list`) | Size |
|---|---|---|
| llama3:latest | 365c0bd3c000 | 4.7 GB |
| mistral:latest | f974a74358d6 | 4.1 GB |
| tinyllama:latest | 2644915ede35 | 637 MB |
| mxbai-embed-large:latest | 468836162de7 | |
| all-minilm:latest | 1b226e2802db | |

The ids are those of the original machine. A job records whether each tag still resolves to its id. Both implementations run with each of llama3, mistral and tinyllama.

## 4. The manual

The manual meets all of these criteria:

- Civilian, and either a public-domain government manual or a manufacturer manual that is publicly downloadable.
- An operation and maintenance manual for industrial process or rotating equipment such as a compressor, generator set, engine or boiler.
- 100 pages or more.
- One manual that covers several models or frames and states which procedures or features apply to which.
- At least one feature that applies to some variants and is explicitly excluded for others. The central failure case is a procedure returned for a variant the manual excludes.
- Procedures with prerequisites and numbered steps, some crossing page boundaries.
- Tables of limits or settings.
- Terms that allow this use. The URL, revision, download date and checksum are recorded.

A manufacturer manual is fetched in the job from its public URL and is never committed. A military manual is a fallback only. Candidates and their verification are in `docs/manual_candidates.md`.

## 5. The question set

`questions/questions.csv` holds questions worded the way an operator asks them. The target is 40 questions, 8 per category. If the measured runner budget does not allow it, `results/notes.md` states how many fit and which categories were reduced. Columns: `id`, `category`, `question`, `reference_answer`, `source_pages`, `exclusion_pages` (applicability questions only: the pages that state the exclusion), `required_elements`, `verified_by`, `verified_on`.

| Category | Target (minimum) | What it tests | Original example it mirrors |
|---|---|---|---|
| Self-contained procedure | 8 (5) | The answer sits in one section | Setting a trip pressure: answered correctly |
| Condition-dependent procedure | 8 (5) | The answer depends on an operating condition and on steps kept together | Protecting a unit under high load: returned a description of a display indicator |
| Applicability | 8 (5) | The correct answer is that the feature does not apply to the variant asked about | Automatic pressure test on an excluded variant: A gave a procedure, B declined |
| Unanswerable | 8 (4) | The manual has no answer; the correct behaviour is to say so | |
| Table lookup | 8 (3) | A value from a table | |

`required_elements` lists what a correct answer must contain, such as each prerequisite, the step count or the exclusion. Scoring uses it. Nothing is scored before `verified_by` is filled in.

## 6. Experiments

**E1. Baseline grid.** Implementation A and Implementation B each run with llama3, mistral and tinyllama: six cells on the same question set. The grid reproduces the observations of the article and removes the confound between prompt and model size from the baseline. If the six cells do not fit the runner budget, `results/notes.md` reports the measured numbers and a proposed run order. No cell is dropped silently.

**E2. One factor at a time.** Start from Implementation B and change a single setting per run. One model is used throughout. It is chosen after the budget measurement, and `results/notes.md` states which and why.

| Run | Change |
|---|---|
| E2a | Chunking: page-level, 1,000-character sentence groups, and procedure-preserving (split on headings, keep a procedure's prerequisites and steps in one chunk) |
| E2b | Grounding instruction: "supplement" versus "say you don't know" |
| E2c | Generation settings: with and without the line-break stop and the shortest-answer instruction |
| E2d | Relevance threshold: none versus a threshold that lets retrieval return nothing |
| E2e | Model size: smaller versus larger model, same prompt |
| E2f | Query rewriting: off versus on |

E2a and E2e together test whether chunking matters more than model choice. E2b and E2e together separate prompt from model size in the applicability case.

**E3. The gate.** `gate/src/DeterministicGate.cs` is the gate described in the article. It was compiled into the original build and never exercised there. The state reader in E3 is a stand-in with fixed values, and results say so.

1. Unit tests cover every reason code (`gate/tests`).
2. Scripted proposals: the eleven in `gate/src/Program.cs` plus cases at the boundary of each rule. Accepted and refused counts are reported by reason code.
3. Model-generated proposals: each language model receives the typed action schema and 24 operator requests, some reasonable, some outside the envelope, some asking to inhibit a trip. The raw model output goes to `DeterministicGate.Evaluate(string)`. We report how many outputs parsed, how many were accepted and how many refused, by reason code.
4. Adversarial requests: 10 prompts that tell the model to ignore limits. We report whether any out-of-envelope action was accepted. The expected count is zero, and the count is what is reported.

**E4. Resource use.** For each pipeline: peak resident memory of the Ollama process and of the pipeline process, time to build the index, index size on disk and time per answer. These are runner measurements and are reported as such.

**E5 (low priority). Documentation in the prompt.** Manual text is placed directly in the prompt with the default context window, as in a custom model built from mistral in the original builds. We record `num_ctx`, `prompt_eval_count` and whether the prompt was truncated, and keep the answers for marking.

## 7. Scoring

Two levels, kept separate.

**Retrieval (automatic).** Did the retrieved chunks include the reference pages? We report hit rate per category. For applicability questions we also report whether the chunk holding the exclusion was retrieved.

**Answer (marked by a person).** For each answer the marking sheet carries the question, the reference answer, the required elements, the raw answer and empty marking columns:

- `correct`: yes, partial, no
- `complete`: all required elements present
- `respects_applicability`: for applicability questions
- `abstained`: the answer says the manual does not cover it
- `unsupported_content`: the answer contains material not in the retrieved text

A suggested mark from string checks against `required_elements` is kept in a separate file. The person's mark is the one reported. A language model is not the judge of record.

**Blind marking.** The sheet hides which configuration produced each answer. Rows are shuffled with a fixed seed and each row gets a neutral answer id. The key that maps answer ids to configurations is a separate file that is not opened until marking is finished. Reference answers are verified before any model answer is shown.

**Reporting.** Counts are given as n of N, never as a percentage alone. The per-question outcome of every configuration is published as a question-by-configuration table, so paired comparisons can be read off.

## 8. Outputs

```
config/pipelines.json      settings of both pipelines
pipelines/a_python/        Implementation A
pipelines/b_dotnet/        Implementation B
gate/                      gate, tests, proposal sets, harnesses
questions/questions.csv
scoring/                   validator, retrieval scorer, blind export, mark joining
results/<run-id>/          answers, retrieval, gate and resource files, env.txt
results/summary.md         one table per experiment with run ids, then limitations
results/notes.md           deviations, failures, the claim-to-experiment table
.github/workflows/         the jobs
```

`results/summary.md` leads with the E1 table: configuration by category, retrieval hit rate and answers correct out of the number asked. It is kept current after every run and ends with a limitations section: one manual, one marker, small models on a 4-CPU runner, and a re-implementation rather than the original builds.

`results/notes.md` lists which experiment tests which claim of the article. If runner time is the binding limit, it states what larger runners would change in numbers of questions and repeats, from measured timings.

## 9. Sequence

1. The `manual-models-budget` workflow verifies the manual candidates, records whether the model tags resolve to the original ids, and measures prompt-processing speed on real manual text.
2. The gate is tested (E3 steps 1 and 2 need no model).
3. Implementation A and Implementation B are run on the chosen manual.
4. The question set is drafted and its reference answers are verified.
5. E1, then E3 steps 3 and 4, then E2. E4 is collected along the way. E5 runs last.
