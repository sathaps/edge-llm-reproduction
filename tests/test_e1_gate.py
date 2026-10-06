import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import e1_gate as g  # noqa: E402

QIDS = [r["id"] for r in csv.DictReader(open(ROOT / "questions" / "questions.csv"))]


def make(d, answers=None, drop_key=None):
    d.mkdir(parents=True)
    rows = answers or [{"question_id": q, "answer": f"ok {q}", "wall_s": 1.0, "prompt_eval_count": 500, "eval_count": 5, "context_length": 4096,
                        "tokens_offered": 500, "tokens_dropped": 0, "prompt_truncated": False} for q in QIDS]
    if drop_key:
        rows[3].pop(drop_key)
    open(d / "answers.jsonl", "w").writelines(json.dumps(r) + "\n" for r in rows)
    open(d / "retrieval.jsonl", "w").writelines(json.dumps({"question_id": q, "retrieved": []}) + "\n" for q in QIDS)
    json.dump({"commit": "abc", "ollama_version": "0.35.1", "model_digest": "d"}, open(d / "run.json", "w"))
    json.dump({}, open(d / "garbled.json", "w"))


def test_passes_and_names_failures(tmp_path):
    make(tmp_path / "A" / "rep-1")
    stats, fails = g.gate_cell(tmp_path / "A" / "rep-1", QIDS)
    assert fails == [] and stats["answers"] == 40
    bad = [{"question_id": q, "answer": "Error: HTTP 500 from server" if i == 2 else "fine", "wall_s": 1, "prompt_eval_count": 5, "eval_count": 1,
            "context_length": 4096, "tokens_offered": 5, "tokens_dropped": 0, "prompt_truncated": False} for i, q in enumerate(QIDS)]
    make(tmp_path / "B" / "rep-1", bad)
    assert any("looks like an error" in f for f in g.gate_cell(tmp_path / "B" / "rep-1", QIDS)[1])
    make(tmp_path / "C" / "rep-1", drop_key="tokens_offered")
    assert any("tokens_offered is missing" in f for f in g.gate_cell(tmp_path / "C" / "rep-1", QIDS)[1])
    make(tmp_path / "D" / "rep-1", bad[:39])
    assert any("expected 40" in f for f in g.gate_cell(tmp_path / "D" / "rep-1", QIDS)[1])
    assert g.main([str(tmp_path), "1", "--cells", "A,B"]) == 1
