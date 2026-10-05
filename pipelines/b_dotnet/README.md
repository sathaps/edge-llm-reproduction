# Implementation B

A C# port of LangChain with its SQLite vector store. Packages at version 0.17.0: `LangChain`, `LangChain.Databases.Sqlite`, `LangChain.Providers.Ollama`, `LangChain.DocumentLoaders.Pdf`. The version used originally is not known.

    dotnet run --project pipelines/b_dotnet -- --pdf MANUAL.pdf --model llama3:latest --out results/<run-id> [--ollama URL] [--questions CSV] [--set path=value] [--conversation fresh|chained] [--retrieval-only]

Settings are in `config/pipelines.json`, section `b`.

Behaviour of the packages that we observed and keep as it is:

- The provider calls `/api/embeddings`, one text per request.
- `SqLiteVectorDatabase` uses Euclidean distance unless told otherwise.
- The collection is declared with 1536 dimensions, as in the original build, while `all-minilm` returns 384. In a run against a stub that returned 384-dimension vectors, adding and searching did not throw. This needs a check against the real model.
- `VectorSearchSettings.ScoreThreshold` has no effect in the SQLite store. A threshold is applied on the returned distance in `Program.cs`.
- `RelevanceScore` is 0 for every hit, so the run records `distance` and leaves `score` null.
