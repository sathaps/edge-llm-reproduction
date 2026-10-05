import csv, json, random
from pathlib import Path

import rubric
from questions import verified

MARKS = ["correct", "complete", "respects_applicability", "abstained"]
def load_run(run_dir):
    run_dir = Path(run_dir)
    answers = [json.loads(l) for l in open(run_dir / "answers.jsonl")]
    retrieval = {r["question_id"]: r for r in map(json.loads, open(run_dir / "retrieval.jsonl"))}
    chunks = {c["chunk_id"]: c for c in map(json.loads, open(run_dir / "chunks.jsonl"))}
    return answers, retrieval, chunks


def context_texts(ret_row, chunks):
    """The context texts behind one answer. The oracle bracket stores the given pages in the retrieval row itself."""
    if ret_row.get("given_text") is not None:
        return [ret_row["given_text"]] if ret_row["given_text"] else []
    return [chunks[h["chunk_id"]]["text"] for h in ret_row["retrieved"]]


def export(runs, questions, out_dir, seed):
    """runs: {config_id: run_dir}. Writes the blind sheet, the support sheet, the rubric's marks and the key.

    Identical answer texts to the same question are shown once. The key lists every configuration behind an answer id.
    """
    qs = {q["id"]: q for q in verified(questions)}
    groups = {}
    for config_id, run_dir in runs.items():
        answers, retrieval, chunks = load_run(run_dir)
        for a in answers:
            qid = a["question_id"]
            if qid not in qs:
                continue
            context = "\n---\n".join(context_texts(retrieval[qid], chunks))
            g = groups.setdefault((qid, " ".join(a["answer"].split())), {"answer": a["answer"], "qid": qid, "members": [], "contexts": []})
            g["members"].append((config_id, str(run_dir)))
            if context not in g["contexts"]:
                g["contexts"].append(context)
    rows = list(groups.values())
    random.Random(seed).shuffle(rows)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    blind, support, auto, key = [], [], [], []
    for n, g in enumerate(rows, 1):
        aid = f"ans-{n:04d}"
        q = qs[g["qid"]]
        blind.append({"answer_id": aid, "question": q["question"], "reference_answer": q["reference_answer"],
                      "required_elements": q["required_elements"], "forbidden_elements": q.get("forbidden_elements", ""), "category": q["category"], "answer": g["answer"],
                      **{m: "" for m in MARKS}})
        support.append({"answer_id": aid, "retrieved_text": "\n=====\n".join(g["contexts"]), "unsupported_content": ""})
        auto.append({"answer_id": aid, **rubric.score_answer(q, g["answer"], " ".join(g["contexts"]))})
        for config_id, run_dir in g["members"]:
            key.append({"answer_id": aid, "config_id": config_id, "question_id": g["qid"], "run_dir": run_dir})
    for name, data in (("sheet_blind.csv", blind), ("sheet_support.csv", support), ("rubric_marks.csv", auto), ("key.csv", key)):
        with open(out / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]) if data else [])
            w.writeheader()
            w.writerows(data)
    json.dump({"seed": seed, "answers_shown": len(rows), "answers_total": len(key)}, open(out / "export.json", "w"))
    return key


def second_marker_sample(out_dir, size=60, seed=7):
    """Write a random sample of the blind sheet for a second marker. The sample has no key and empty marking columns."""
    out = Path(out_dir)
    rows = list(csv.DictReader(open(out / "sheet_blind.csv", newline="")))
    sample = sorted(random.Random(seed).sample(rows, min(size, len(rows))), key=lambda r: r["answer_id"])
    for r in sample:
        for m in MARKS:
            r[m] = ""
    with open(out / "sheet_second_marker.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(sample[0]))
        w.writeheader()
        w.writerows(sample)
    json.dump({"seed": seed, "size": len(sample), "of": len(rows)}, open(out / "second_marker.json", "w"))
    return [r["answer_id"] for r in sample]
