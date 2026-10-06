# Results of record

Every table in `results/summary.md` and every measured table in `results/notes.md` is listed here with the runs and the commit that produced it. A table that is not listed is not a result of record. The raw files are in the directories named in the last column.

| Entry | Table | Run ids | Commit | Files |
|---|---|---|---|---|
| `runner-measurements` | Runner, tag resolution, context windows, speed (summary: Runner measurements; notes: budget tables) | 37375097339 (`manual-models-budget`) | 05615c8 | `results/run-37375097339-manual-models-budget/` |
| `gate-e3-steps-1-2` | Gate unit tests and scripted proposals | 37375097256 (`gate-tests`); scripted proposals in a development container | 05615c8 | `results/gate/` |
| `prompt-truncation` | Check 1: tokens offered and used per model (notes) | 37380524685 (`truncation-checks`), all three models. Run 37379679812 is the first version of the check, kept for the record | de753aa | `results/run-37380524685-truncation-checks/`, `results/run-37379679812-truncation-checks/` |
| `embedding-truncation` | Check 2: full page against page cut to the window (notes) | 37380524685, job `embed`. Run 37382524262 repeated the check, its `embed` job failed while installing Ollama and gave no result | de753aa | `results/run-37380524685-truncation-checks/` |
| `mistral-tags` | Search for a mistral tag with the original id (notes) | 37379679812 and 37380524685, job `tags` | 6588afa, de753aa | `results/run-37380524685-truncation-checks/` |
| `prompt-survival` | Which part of an over-long prompt the model sees (notes, probe) | 37391090572, jobs `survival (...)`. Run 37389480081 used the same logic and is not a result | edde00b | job logs of the run, transcribed into `results/notes.md` |
| `embedding-retrieval` | Retrieval of passages beyond the embedding window (notes) | 37386511987, job `retrieval`. The first attempt (37385231341) failed because the legacy endpoint refuses long input. A rerun on the Cummins manual (37389480081) failed on pages without text and is not a result | 2ed114f | `results/run-37386511987-survival-retrieval/` |
| `embedding-retrieval-cummins` | Retrieval of passages beyond the embedding window, Cummins manual (notes) | 37391090572, job `retrieval` | edde00b | job logs of the run, transcribed into `results/notes.md` |
| `period-ollama` | Legacy endpoint and embedding truncation on Ollama 0.3.14 (notes, check 3) | 37387498181, jobs `embeddings` and `chat` (llama3 prompt truncation on 0.3.14) | 93573ef | `results/run-37387498181-ollama-period/` |
| `e1-repeat-1` | E1 table, repeat 1 (summary: E1; notes: E1 repeat 1) | 37394227689 (five cells, commit 62e8c3d); A-mistral rerun from commit b41cea7 (run 37395147521) | 62e8c3d, b41cea7; protocol-v1 at 07f4a33 | `results/e1/` |

Runs that failed or were cancelled stay listed in the notes with the reason. Development-container runs are debugging runs and are never listed here as results.
| `amendment-1` | Protocol amendment 1 (E2k, original window) and amendment 2 (survival arithmetic), `docs/protocol_amendments.md` | none | 1f2329e (added before any E1 answer was collected or read) | `docs/protocol_amendments.md` |
| `amendment-3` | Second corpus not run, `docs/protocol_amendments.md` | none | abfb791 (decided before any E1 answer was collected or read) | `docs/protocol_amendments.md` |
