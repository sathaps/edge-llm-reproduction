# Pipeline settings

`pipelines.json` is the single source of settings for Implementation A and Implementation B. It follows the table in section 3 of `PROTOCOL.md`. Both pipelines read it, and an experiment changes one key through `--set <path>=<json value>`, for example `--set retrieval.top_k=3`.

The relevance threshold is `retrieval.min_score` (cosine similarity, A) and `retrieval.max_distance` (Euclidean distance, B). `null` means no threshold.

The prompt texts (A's system instruction and rewrite template, B's answer template) have not yet been checked against the pinned upstream source.

Output files of one run, written by both pipelines to the run directory:

| File | Content |
|---|---|
| `run.json` | effective settings, model and embedding digests, Ollama version, input file checksum, chunk count, timing |
| `chunks.jsonl` | one row per chunk: `chunk_id`, `pages`, `text` |
| `retrieval.jsonl` | one row per question: retrieved `chunk_id`, `pages`, in rank order, with `score` (cosine similarity, Implementation A) or `distance` (Euclidean, Implementation B) |
| `answers.jsonl` | one row per question: raw answer, token counts, durations, context length in effect, and truncation flags |

Chunking kinds for Implementation B: `page` (default), `sentence_groups` (`max_chars`) and `procedure` (`heading_pattern`, `step_pattern`, `max_chars`). `procedure` starts a chunk at every match of `heading_pattern` and cuts a section longer than `max_chars` at the last `step_pattern` match that fits. The patterns depend on the manual and are set per experiment, for example `--set 'chunking={"kind":"procedure","heading_pattern":"Section \\d+\\.","step_pattern":"Step \\d+","max_chars":6000}'`.
