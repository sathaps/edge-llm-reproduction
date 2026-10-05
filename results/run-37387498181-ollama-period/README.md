Run 37387498181 of the `ollama-period` workflow at commit 93573ef, on GitHub-hosted runners with 4 CPUs and 15 GB. Ollama 0.3.14, the first of the 0.3.x releases the install script tried (0.3.14, then 0.3.13 and older), installed and answered. The server reported version 0.3.14. Fulton manual (SHA-256 `567d20d5…78ab`).

`/api/ps` of this release does not report the context window, so the embedding check takes the trained lengths (256 for all-minilm, 512 for mxbai-embed-large) as the windows. Both are consistent with the tokens used (256 and 512). Releases of this period do not return `prompt_eval_count` on `/api/embeddings`.

`legacy_embed.csv` is transcribed from the job log. `embedding_truncation.csv` is the summary line of each model from the job log. The per-page rows of the embedding check are in workflow artifact `period-embeddings` of the same run. The llama3 prompt check of this run was still running when these files were written.
