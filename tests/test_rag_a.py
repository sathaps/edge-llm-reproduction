import json

import rag_a


def test_flatten_gives_one_start_per_page(pdf_path):
    text, starts = rag_a.flatten_pages(pdf_path)
    assert len(starts) == 4
    assert starts[0] == 0 and starts == sorted(starts)
    assert "\n" not in text and "  " not in text


def test_chunks_stay_under_limit_and_cover_the_text(pdf_path):
    text, starts = rag_a.flatten_pages(pdf_path)
    chunks = rag_a.chunk_text(text, starts, 200)
    assert len(chunks) > 1
    assert all(len(c["text"]) < 200 or "." not in c["text"][:-1] for c in chunks)
    # sentences are glued without a space inside a chunk, so only the characters other than spaces must match
    assert "".join(c["text"] for c in chunks).replace(" ", "") == text.replace(" ", "")


def test_sentences_in_a_chunk_run_together_as_in_the_upstream_script():
    text = "One. Two. Three."
    assert [c["text"] for c in rag_a.chunk_text(text, [0], 1000)] == ["One.Two.Three."]
    # after a cut the first sentence keeps its trailing space, the next ones do not
    five = "Aaaa. Bbbb. Cccc. Dddd. Eeee."
    assert [c["text"] for c in rag_a.chunk_text(five, [0], 20)] == ["Aaaa.Bbbb.Cccc.", "Dddd. Eeee."]
    # a sentence that does not fit next to the previous one is cut off alone
    assert [c["text"] for c in rag_a.chunk_text("Aaaa. Bbbb. Cccc. Dddd.", [0], 12)] == ["Aaaa.Bbbb.", "Cccc.", "Dddd."]


def test_chunk_pages_follow_offsets(pdf_path):
    text, starts = rag_a.flatten_pages(pdf_path)
    chunks = rag_a.chunk_text(text, starts, 1000)
    assert chunks[0]["pages"][0] == 1
    assert max(p for c in chunks for p in c["pages"]) == 4
    assert any(len(c["pages"]) > 1 for c in chunks)


def test_retrieve_respects_top_k_and_threshold():
    import numpy as np
    m = rag_a.normalise(np.array([[1, 0], [0.9, 0.1], [0, 1], [0.5, 0.5]], dtype=float))
    q = rag_a.normalise(np.array([1.0, 0.0]))[0]
    assert len(rag_a.retrieve(q, m, 3, None)) == 3
    assert rag_a.retrieve(q, m, 3, 2.0) == []
    assert rag_a.retrieve(q, m, 3, None)[0][0] == 0


def test_override_changes_one_key():
    cfg = rag_a.load_config("config/pipelines.json", "a", ["retrieval.top_k=7"])
    assert cfg["retrieval"]["top_k"] == 7 and cfg["retrieval"]["min_score"] is None
    assert cfg["chunking"]["max_chars"] == 1000


def test_truncation_flag():
    assert rag_a.truncation_flags(3900, 4096)["prompt_near_context_limit"]
    assert not rag_a.truncation_flags(500, 4096)["prompt_near_context_limit"]
    assert not rag_a.truncation_flags(500, None)["prompt_near_context_limit"]


def run_a(pdf_path, url, tmp_path, *extra):
    q = tmp_path / "q.csv"
    q.write_text("id,question\nq1,How do I start the unit?\nq2,Does model Y support the load test?\n")
    out = tmp_path / "out"
    rag_a.run(rag_a.parse_args(["--pdf", str(pdf_path), "--ollama", url, "--questions", str(q), "--out", str(out),
                                "--model", "llama3:latest", *extra]))
    return out


def test_end_to_end_files_and_grounding_text(pdf_path, url, stub, tmp_path):
    out = run_a(pdf_path, url, tmp_path)
    assert {p.name for p in out.iterdir()} == {"run.json", "chunks.jsonl", "retrieval.jsonl", "answers.jsonl"}
    ret = [json.loads(l) for l in open(out / "retrieval.jsonl")]
    assert [r["question_id"] for r in ret] == ["q1", "q2"]
    assert all(len(r["retrieved"]) <= 3 for r in ret)
    chat = [b for path, b in stub.requests if path == "/api/chat"]
    assert len(chat) == 2
    assert "bring in extra relevant infromation" in chat[0]["messages"][0]["content"]  # the typo is upstream's
    assert "Relevant Context:" in chat[0]["messages"][-1]["content"]
    assert chat[0]["options"] == {"temperature": 0, "seed": 42, "num_predict": 2000}
    run = json.load(open(out / "run.json"))
    assert run["chunks"] == len([1 for _ in open(out / "chunks.jsonl")]) and run["settings"]["embedding_model"] == "mxbai-embed-large"


def test_num_ctx_is_sent_only_when_set(pdf_path, url, stub, tmp_path):
    run_a(pdf_path, url, tmp_path, "--set", "generation.num_ctx=8192")
    chat = [b for p, b in stub.requests if p == "/api/chat"]
    assert chat[0]["options"]["num_ctx"] == 8192


def test_no_rewrite_in_fresh_conversations(pdf_path, url, stub, tmp_path):
    run_a(pdf_path, url, tmp_path)
    assert len([b for p, b in stub.requests if p == "/api/chat"]) == 2


def test_rewrite_from_second_turn_when_chained(pdf_path, url, stub, tmp_path):
    out = run_a(pdf_path, url, tmp_path, "--conversation", "chained")
    chat = [b for p, b in stub.requests if p == "/api/chat"]
    assert len(chat) == 3  # one rewrite before the second answer
    rewrite = chat[1]["messages"][0]
    assert rewrite["role"] == "system" and rewrite["content"].startswith("Rewrite the following query")
    # the history in the prompt is the last two messages including the current question
    assert "assistant: stub answer" in rewrite["content"] and "user: Does model Y support the load test?" in rewrite["content"]
    ret = [json.loads(l) for l in open(out / "retrieval.jsonl")]
    assert ret[0]["query_used"] == "How do I start the unit?" and ret[1]["query_used"] == "stub answer"


def test_retrieval_only_makes_no_chat_calls(pdf_path, url, stub, tmp_path):
    out = run_a(pdf_path, url, tmp_path, "--retrieval-only")
    assert not [1 for p, _ in stub.requests if p == "/api/chat"]
    assert not (out / "answers.jsonl").exists()
