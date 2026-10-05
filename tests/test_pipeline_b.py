import json, shutil, subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(shutil.which("dotnet") is None, reason="dotnet is not installed")


@pytest.fixture(scope="module")
def dll(tmp_path_factory):
    out = tmp_path_factory.mktemp("b_build")
    subprocess.run(["dotnet", "build", str(ROOT / "pipelines/b_dotnet"), "-o", str(out), "-v", "q"], check=True, capture_output=True)
    return out / "PipelineB.dll"


def run_b(dll, pdf_path, url, tmp_path, *extra):
    q = tmp_path / "q.csv"
    q.write_text("id,question\nq1,How do I start the unit?\nq2,Does model Y support the load test?\n")
    out = tmp_path / "out"
    r = subprocess.run(["dotnet", str(dll), "--pdf", str(pdf_path), "--ollama", url, "--questions", str(q), "--out", str(out),
                        "--config", str(ROOT / "config/pipelines.json"), *extra], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-2000:] + r.stdout[-2000:]
    return out


def rows(path):
    return [json.loads(l) for l in open(path)]


def test_page_chunks_and_top_five(dll, pdf_path, url, stub, tmp_path):
    out = run_b(dll, pdf_path, url, tmp_path)
    chunks = rows(out / "chunks.jsonl")
    assert [c["pages"] for c in chunks] == [[1], [2], [3], [4]]
    ret = rows(out / "retrieval.jsonl")
    assert [r["question_id"] for r in ret] == ["q1", "q2"]
    assert all(len(r["retrieved"]) == 4 for r in ret)  # four pages exist, top_k is 5
    run = json.load(open(out / "run.json"))
    assert run["settings"]["embedding_model"] == "all-minilm" and run["settings"]["vector_store"]["collection_dimensions"] == 1536
    assert run["chunks"] == 4 and run["index_bytes"] > 0


def test_prompt_stop_and_determinism(dll, pdf_path, url, stub, tmp_path):
    run_b(dll, pdf_path, url, tmp_path)
    chat = [b for p, b in stub.requests if p == "/api/chat"]
    assert len(chat) == 2
    prompt = chat[0]["messages"][-1]["content"]
    assert "say that you don't know" in prompt and "Keep the answer as short as possible." in prompt
    assert "Question: How do I start the unit?" in prompt and prompt.rstrip().endswith("Helpful Answer:")
    assert prompt.startswith("Use the following pieces of context to answer the question at the end.\nIf the answer is not in context")
    opts = chat[0]["options"]
    assert opts["stop"] == ["\n"] and opts["temperature"] == 0 and opts["seed"] == 42


def test_generation_experiment_switches(dll, pdf_path, url, stub, tmp_path):
    run_b(dll, pdf_path, url, tmp_path, "--set", "generation.stop=null", "--set", "generation.shortest_answer=false")
    chat = [b for p, b in stub.requests if p == "/api/chat"]
    assert "as short as possible" not in chat[0]["messages"][-1]["content"]
    assert not chat[0]["options"].get("stop")


def test_distance_threshold_can_return_nothing(dll, pdf_path, url, stub, tmp_path):
    out = run_b(dll, pdf_path, url, tmp_path, "--set", "retrieval.max_distance=0.0001")
    assert all(r["retrieved"] == [] for r in rows(out / "retrieval.jsonl"))


def test_sentence_group_chunking_and_top_k_override(dll, pdf_path, url, stub, tmp_path):
    out = run_b(dll, pdf_path, url, tmp_path, "--set", 'chunking={"kind":"sentence_groups","max_chars":100}', "--set", "retrieval.top_k=2",
                "--retrieval-only")
    chunks = rows(out / "chunks.jsonl")
    assert len(chunks) > 4 and chunks[0]["chunk_id"].startswith("c")
    assert all(len(r["retrieved"]) == 2 for r in rows(out / "retrieval.jsonl"))
    assert not (out / "answers.jsonl").exists()


def test_no_rewriting_by_default_and_rewriting_when_set(dll, pdf_path, url, stub, tmp_path):
    run_b(dll, pdf_path, url, tmp_path, "--conversation", "chained")
    assert len([1 for p, _ in stub.requests if p == "/api/chat"]) == 2
    stub.requests.clear()
    rw = json.load(open(ROOT / "config/pipelines.json"))["a"]["query_rewriting"]
    out = run_b(dll, pdf_path, url, tmp_path, "--conversation", "chained", "--set", "query_rewriting=" + json.dumps(rw))
    chat = [b for p, b in stub.requests if p == "/api/chat"]
    assert len(chat) == 3 and chat[1]["messages"][0]["content"].startswith("Rewrite the following query")
    assert "user: Does model Y support the load test?" in chat[1]["messages"][0]["content"]
    assert rows(out / "retrieval.jsonl")[1]["query_used"] == "stub answer"


def test_answers_carry_token_counts_and_context(dll, pdf_path, url, stub, tmp_path):
    stub.prompt_tokens = 4000
    out = run_b(dll, pdf_path, url, tmp_path)
    a = rows(out / "answers.jsonl")[0]
    assert a["prompt_eval_count"] == 4000 and a["context_length"] == 4096


PROCEDURE = {"kind": "procedure", "heading_pattern": r"Section \d+\.", "step_pattern": r"Step \d+", "max_chars": 6000}


def test_procedure_chunks_keep_a_section_together_across_pages(dll, pdf_path, url, stub, tmp_path):
    out = run_b(dll, pdf_path, url, tmp_path, "--set", "chunking=" + json.dumps(PROCEDURE), "--retrieval-only")
    chunks = rows(out / "chunks.jsonl")
    assert [c["pages"] for c in chunks] == [[1, 2], [3], [4]]
    assert chunks[0]["text"].startswith("Section 1.") and "Step 5." in chunks[0]["text"] and "Step 1." in chunks[0]["text"]
    assert chunks[1]["text"].startswith("Section 2.") and chunks[2]["text"].startswith("Section 3.")
    assert all(c["chunk_id"].startswith("h") for c in chunks)


def test_procedure_section_longer_than_the_limit_is_cut_at_a_step(dll, pdf_path, url, stub, tmp_path):
    small = {**PROCEDURE, "max_chars": 250}
    out = run_b(dll, pdf_path, url, tmp_path, "--set", "chunking=" + json.dumps(small), "--retrieval-only")
    chunks = rows(out / "chunks.jsonl")
    assert len(chunks) > 3
    assert all(len(c["text"]) <= 250 for c in chunks)
    assert any(c["text"].startswith("Step ") for c in chunks)


def test_embedding_endpoint_is_selectable(dll, pdf_path, url, stub, tmp_path):
    run_b(dll, pdf_path, url, tmp_path, "--retrieval-only")
    assert any(p == "/api/embed" for p, _ in stub.requests) and not any(p == "/api/embeddings" for p, _ in stub.requests)
    stub.requests.clear()
    (tmp_path / "legacy").mkdir()
    run_b(dll, pdf_path, url, tmp_path / "legacy", "--retrieval-only", "--set", "embedding_endpoint=\"legacy\"")
    assert any(p == "/api/embeddings" for p, _ in stub.requests) and not any(p == "/api/embed" for p, _ in stub.requests)
