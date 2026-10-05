Run 37380524685 of the `truncation-checks` workflow at commit de753aa, on GitHub-hosted runners with 4 CPUs and 15 GB (Ollama 0.35.1, CPU only). The prompts and pages come from the Fulton manual (132 pages, SHA-256 `567d20d5…78ab`), fetched in the job.

The files are transcribed from the job logs. Values are copied, not rounded. The per-page rows of the embedding check are in workflow artifact `embedding-truncation` of the same run.

`tokens_dropped` in `prompt_truncation_tinyllama.csv` is the logged `offered - used`. For rows where `truncated` is false it is the error of the piecewise count (at most 8 tokens, shown by the gap to `tokens_single_raised_pass`), not dropped text. The script now writes 0 for such rows.
