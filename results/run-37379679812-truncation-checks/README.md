Run 37379679812 of the `truncation-checks` workflow at commit 6588afa, on a GitHub-hosted runner with 4 CPUs and 15 GB (Ollama 0.35.1, CPU only), Fulton manual (SHA-256 `567d20d5…78ab`).

This was the first version of the prompt check. It counts the tokens offered with a single pass at `num_ctx` 32768. For mistral that is valid, because the raised window of 32768 held every prompt. For llama3 (trained length 8192) and tinyllama (2048) the single pass could not count the longest prompts, so their rows are in `results/run-37380524685-truncation-checks/` with the piecewise count. The corrected run's mistral job has since finished, and its rows are in `results/run-37380524685-truncation-checks/prompt_truncation_mistral.csv`. They differ from the rows here by one token or two, and the notes use the corrected run.

The file is transcribed from the job log. Values are copied, not rounded.
