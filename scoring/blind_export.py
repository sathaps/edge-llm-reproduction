import csv, json, random, re
from pathlib import Path

from questions import verified, elements

MARKS = ["correct", "complete", "respects_applicability", "abstained"]
ABSTAIN = re.compile(r"(do not|don't|doesn't|does not) know|not (covered|mentioned|specified|stated|provided)|"
                     r"(cannot|can't|unable to) (find|determine)|no (information|mention)", re.I)


def load_run(run_dir):
    run_dir = Path(run_dir)
    answers = [json.loads(l) for l in open(run_dir / "answers.jsonl")]
    retrieval = {r["question_id"]: r for r in map(json.loads, open(run_dir / "retrieval.jsonl"))}
    chunks = {c["chunk_id"]: c for c in map(json.loads, open(run_dir / "chunks.jsonl"))}
    return answers, retrieval, chunks


def suggest(answer, required):
    low = answer.lower()
    hit = [e for e in required if e.lower() in low]
    return {"suggested_complete": "yes" if len(hit) == len(required) else "no",
            "suggested_elements_found": f"{len(hit)} of {len(required)}",
            "suggested_abstained": "yes" if ABSTAIN.search(answer) else "no"}


def export(runs, questions, out_dir, seed):
    """runs: {config_id: run_dir}. Writes the blind sheet, the support sheet, suggestions and the key."""
    qs = {q["id"]: q for q in verified(questions)}
    rows = []
    for config_id, run_dir in runs.items():
        answers, retrieval, chunks = load_run(run_dir)
        for a in answers:
            if a["question_id"] not in qs:
                continue
            ids = [h["chunk_id"] for h in retrieval[a["question_id"]]["retrieved"]]
            rows.append({"config_id": config_id, "run_dir": str(run_dir), "answer": a["answer"],
                         "question_id": a["question_id"], "retrieved_text": "\n---\n".join(chunks[i]["text"] for i in ids)})
    random.Random(seed).shuffle(rows)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    blind, support, sugg, key = [], [], [], []
    for n, r in enumerate(rows, 1):
        aid = f"ans-{n:04d}"
        q = qs[r["question_id"]]
        blind.append({"answer_id": aid, "question": q["question"], "reference_answer": q["reference_answer"],
                      "required_elements": q["required_elements"], "category": q["category"], "answer": r["answer"],
                      **{m: "" for m in MARKS}})
        support.append({"answer_id": aid, "retrieved_text": r["retrieved_text"], "unsupported_content": ""})
        sugg.append({"answer_id": aid, **suggest(r["answer"], elements(q["required_elements"]))})
        key.append({"answer_id": aid, "config_id": r["config_id"], "question_id": r["question_id"], "run_dir": r["run_dir"]})
    for name, data in (("sheet_blind.csv", blind), ("sheet_support.csv", support), ("suggestions.csv", sugg), ("key.csv", key)):
        with open(out / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]) if data else [])
            w.writeheader()
            w.writerows(data)
    json.dump({"seed": seed, "rows": len(rows)}, open(out / "export.json", "w"))
    return key
