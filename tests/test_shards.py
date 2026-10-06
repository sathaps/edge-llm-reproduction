import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import make_shard, merge_shards  # noqa: E402

QIDS = [r["id"] for r in csv.DictReader(open(ROOT / "questions" / "questions.csv"))]


def test_slices_cover_the_file_in_order():
    rows = list(range(40))
    for n in (1, 2, 3, 4):
        parts = [make_shard.shard_rows(rows, k, n) for k in range(1, n + 1)]
        assert sum(parts, []) == rows


def test_merge(tmp_path):
    n = 4
    for k in range(1, n + 1):
        ids = make_shard.shard_rows(QIDS, k, n)
        d = tmp_path / f"shard-{k}-of-{n}" / "B-llama3" / "rep-1"
        d.mkdir(parents=True)
        open(d / "answers.jsonl", "w").writelines(json.dumps({"question_id": q, "answer": "x"}) + "\n" for q in ids)
        open(d / "retrieval.jsonl", "w").writelines(json.dumps({"question_id": q, "retrieved": []}) + "\n" for q in ids)
        json.dump({"commit": "abc", "ollama_version": "0.35.1" if k < 4 else "0.35.2", "model_digest": "d"}, open(d / "run.json", "w"))
        json.dump({"chunks": 155, "questions": len(ids), "retrieved_slots": 5 * len(ids), "garbled_slots": 1, "questions_with_a_garbled_chunk": 1}, open(d / "garbled.json", "w"))
    done, missing = merge_shards.merge(tmp_path)
    out = tmp_path / "B-llama3" / "rep-1"
    assert missing == [] and [json.loads(l)["question_id"] for l in open(out / "answers.jsonl")] == QIDS
    run = json.load(open(out / "run.json"))
    assert run["shards"] == 4 and "ollama_version" in run["shard_mismatch"]
    g = json.load(open(out / "garbled.json"))
    assert g["questions"] == 40 and g["garbled_slots"] == 4 and g["chunks"] == 155
    (tmp_path / "shard-3-of-4" / "B-llama3" / "rep-1" / "answers.jsonl").unlink()
    assert merge_shards.merge(tmp_path)[1]
