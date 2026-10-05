# edge-llm-reproduction

Reproduction of two retrieval pipelines and a deterministic gate for language models on edge devices, run on a public equipment manual.

Status: in setup. See `results/summary.md` for what has been measured.

This repository re-implements, on public material, two configurations of a document question-answering pipeline that were first built for an industrial field computer. It also exercises a small deterministic gate that checks actions proposed by a language model. The original builds, their documentation and their hardware are not part of this repository, and no result here was measured on them.

## Layout

| Path | Content |
|---|---|
| `PROTOCOL.md` | Experiment protocol: configurations, manual criteria, experiments, scoring, rules. Start here. |
| `config/pipelines.json` | Single source of settings for both pipelines |
| `pipelines/a_python/` | Implementation A, single-file retrieval over Ollama |
| `pipelines/b_dotnet/` | Implementation B, C# port of LangChain with the SQLite vector store |
| `questions/` | Question set template and its description |
| `scoring/` | Question validator, retrieval scorer, blind marking export, mark joining |
| `gate/src/` | The gate and a demo of eleven proposals |
| `gate/tests/` | Gate unit tests, one or more per reason code |
| `gate/scripted/`, `gate/proposals/` | Scripted proposal harness, and the request sets for model-generated proposals |
| `gate/modelrun/`, `gate/modeltests/` | Harness that sends operator requests to a model and passes the raw reply to the gate; tests for its ground-truth check |
| `tools/stub_ollama.py` | A fake Ollama endpoint, used by the tests only |
| `tests/` | Python tests for pipeline A, pipeline B, scoring and the model harness, all against the stub |
| `scripts/`, `.github/workflows/`, `manuals/` | Probe scripts, workflows and the list of candidate manual URLs |
| `results/` | Measured results, `summary.md` first |

## Running

    python3 -m pytest tests
    dotnet test gate/tests
    dotnet test gate/modeltests
    python3 pipelines/a_python/rag_a.py --pdf MANUAL.pdf --model llama3:latest --out results/<run-id>
    dotnet run --project pipelines/b_dotnet -- --pdf MANUAL.pdf --model llama3:latest --out results/<run-id>
    dotnet run --project gate/modelrun -- --requests gate/proposals/requests.json --model llama3:latest --out results/<run-id>

Both pipelines accept `--ollama URL`, `--questions CSV`, `--set path=value`, `--conversation fresh|chained` and `--retrieval-only`. Python dependencies are in `pipelines/a_python/requirements.txt`; the tests also need `pytest` and `fpdf2`.

## Rules for results

- Every number reported from this repository comes from a run recorded here, with its commit, model tags and runner hardware.
- No number is estimated, rounded up, or carried over from the original builds.
- Reference answers in the question set are verified by a person against the manual before any scoring.
- Nothing produced against the stub endpoint is a result.
