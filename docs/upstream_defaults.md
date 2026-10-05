# Upstream defaults

We checked the defaults of both implementations against their upstream sources on 2026-10-05. The sources were read from the `main` branch through `raw.githubusercontent.com`. We could not read a commit id, so each file is pinned by its SHA-256.

| File | SHA-256 |
|---|---|
| `AllAboutAI-YT/easy-local-rag`, `localrag.py` | `f0033e9c1b217ba8a1f0a305c24abd092a58919bdafce2b6e9e0fdaf9ada66a6` |
| `AllAboutAI-YT/easy-local-rag`, `upload.py` | `78dca9a43c3e7be922a8e33b6c67d543896e15c56c51c58e7c90e288a49b65c1` |
| `AllAboutAI-YT/easy-local-rag`, `requirements.txt` | `6a2233e740c54f69d63a89065eb9d1688fc42ea53f4860fcfa79f4bf07b3c1d1` |
| `tryAGI/LangChain`, `README.md` | `0ce71328a6ac57f6f72a81b79faffd54be814b435d8fb9a100bb9d3f2e7dc851` |

## Implementation A (easy-local-rag)

| Setting | Upstream | Ours | Status |
|---|---|---|---|
| Embedding model | `mxbai-embed-large`, one `ollama.embeddings` call per line of `vault.txt` | same model, batched `/api/embed` calls; each chunk gets a trailing newline, as the lines of `vault.txt` have | same |
| Text extraction | PyPDF2, pages joined with a space, whitespace collapsed | `pypdf`, the same joining | differs in the library, so page text can differ slightly |
| Chunking | sentences split after `.`, `!` or `?`; a chunk grows while its length plus the next sentence plus 1 stays under 1000 | same rule | same |
| Joining inside a chunk | `(sentence + " ").strip()`, so sentences run together without a space; only the first sentence after a cut keeps its trailing space | same | same, and unexpected. `Step 4.Release` is the result |
| Empty first chunk | a first sentence of 999 characters or more appends an empty chunk | empty chunks are skipped | differs, rarely matters |
| Retrieval | cosine similarity with `torch`, `top_k=3`, no threshold | cosine similarity with `numpy`, `top_k=3`, no threshold | same |
| System message | "You are a helpful assistant ... Also bring in extra relevant infromation ..." | the same text, including the misspelling | same |
| User message | question, then `\n\nRelevant Context:\n`, then the chunks joined by newlines | same | same |
| Query rewriting | from the second turn, when the history holds more than the current question | same | same |
| Rewriting history | the last two messages after the current question has been added | same | same (an earlier version of ours left the current question out and was corrected) |
| Rewriting call | prompt sent with the `system` role, `max_tokens=200`, `temperature=0.1` | `system` role, 200 tokens, temperature 0 | differs in temperature, for determinism |
| Chat call | OpenAI-compatible endpoint, `max_tokens=2000`, no temperature set | `/api/chat`, `num_predict=2000`, temperature 0 and seed 42 | differs in temperature and seed, for determinism. Upstream samples at Ollama's default temperature |
| Context window | not set, so Ollama's default | not set | same |
| Default model | `llama3` | `llama3:latest` | same |

## Implementation B (LangChain .NET)

The only source we could read is the README example of the `tryAGI/LangChain` project, which we take to be what the original build followed. We could not check that against the original.

| Setting | README example | Ours | Status |
|---|---|---|---|
| Vector store | `SqLiteVectorDatabase`, Euclidean distance by default | same | same |
| Collection | `dimensions: 1536`, with the comment that this is right for an OpenAI embedding model | 1536 with `all-minilm`, which gives 384 | same as the build described |
| Loading | `AddDocumentsFromAsync<PdfPigPdfLoader>(..., textSplitter: null)` | the same loader, one chunk per page | same. The README comment says the default splitter would cut chunks of 4000 characters with an overlap of 200; the signature in package 0.17.0 defaults to no splitter |
| Retrieval | `GetSimilarDocuments(embeddingModel, question, amount: 5)`; the package default is 4 | 5 | same |
| Joining the retrieved text | `AsString()`, which separates documents with a blank line | blank line | same |
| Prompt | "Use the following pieces of context ... Keep the answer as short as possible.", one sentence per line, then the context, `Question:` and `Helpful Answer:` | the same lines | same. The chain example in the README has a different closing sentence ("Always quote the context"); we do not use it |
| Stop at the first line break | not in the README | `Stop = "\n"` from the original description | as described |

Behaviour of the package that we keep: the SQLite store ignores `VectorSearchSettings.ScoreThreshold`, and `RelevanceScore` is 0 for every hit. See `pipelines/b_dotnet/README.md`.
