#!/usr/bin/env python3
"""Score the answers of collected runs with the automatic scorer only.

usage: auto_score.py <questions.csv> <out.csv> <results-dir> [rep ...]
Reads <results-dir>/<cell>/rep-N/answers.jsonl and scores each answer with scoring/rubric.py. The retrieved text is not
available in the repository (chunks.jsonl stays in the artifact), so `unsupported_content` and the numbers-not-in-context
column are not computed and are left out. No person has marked these answers. The columns are the scorer's, not marks.
"""
import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scoring"))
import questions as qmod, rubric  # noqa: E402

FIELDS = ["cell", "rep", "question_id", "category", "correct", "complete", "respects_applicability", "abstained", "elements_found", "forbidden_found", "elements_in_order"]


def score(questions_csv, results_dir, reps=None):
    qs = {q["id"]: q for q in qmod.verified(qmod.read_questions(questions_csv))}
    rows = []
    for d in sorted(Path(results_dir).glob("*/rep-*")):
        rep = int(d.name.split("-")[1])
        if reps and rep not in reps or not (d / "answers.jsonl").exists():
            continue
        for line in open(d / "answers.jsonl"):
            a = json.loads(line)
            if a["question_id"] in qs:
                s = rubric.score_answer(qs[a["question_id"]], a["answer"], "")
                rows.append({"cell": d.parent.name, "rep": rep, "question_id": a["question_id"], "category": qs[a["question_id"]]["category"],
                             **{k: s[k] for k in FIELDS[4:]}})
    return rows


if __name__ == "__main__":
    reps = [int(x) for x in sys.argv[4:]]
    rows = score(sys.argv[1], sys.argv[3], reps)
    with open(sys.argv[2], "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "rows")
