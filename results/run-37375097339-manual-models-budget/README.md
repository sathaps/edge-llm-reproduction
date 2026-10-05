Run 37375097339 of the `manual-models-budget` workflow at commit 05615c8, job 111981630717, on a GitHub-hosted runner.

The files here are transcribed from the job log. Values are copied, not rounded; the two `derived_` columns in `budget_calls.csv` are our arithmetic on logged values. The original outputs, including the model answers of the budget calls, are in workflow artifact `manual-models-budget` of the same run.

The budget prompts were built from the text of the first candidate with 100 or more pages, which was the AERCO manual (`manuals.csv`). They are timing probes and not question-set results.

Notes on the columns:

- In `budget_calls.csv`, repeat 2 of each prompt reuses Ollama's prompt cache (prompt evaluation takes a fraction of a second), so `derived_prompt_tokens_per_s` is left empty for it.
- In `setup_probes.csv`, `pull_wall_s` is the time of a second pull of a model that an earlier step had already pulled. It is not a download time. The step that pulled all six tags took 21:27:48Z to 21:28:43Z.
