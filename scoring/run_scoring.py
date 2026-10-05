#!/usr/bin/env python3
"""Command line for the scoring steps.

  run_scoring.py validate questions/questions.csv
  run_scoring.py retrieval questions/questions.csv OUT.csv LABEL=RUN_DIR [LABEL=RUN_DIR ...]
  run_scoring.py export questions/questions.csv OUT_DIR SEED LABEL=RUN_DIR [LABEL=RUN_DIR ...]
  run_scoring.py join MARKING_DIR OUT_DIR
  run_scoring.py score questions/questions.csv OUT.csv LABEL=RUN_DIR [LABEL=RUN_DIR ...]
  run_scoring.py agreement MARKING_DIR
  run_scoring.py second-marker MARKING_DIR [SIZE [SEED]]
  run_scoring.py second-agreement MARKING_DIR SECOND_SHEET.csv
  run_scoring.py analyze OUTCOMES.csv experiments/comparisons.json OUT_PREFIX
  run_scoring.py tables retrieval|exclusion|correct ...   (see summary_tables.py)
"""
import csv
import json
import sys
from pathlib import Path

import agreement, blind_export, marks, questions, retrieval_score, rubric, summary_tables


def runs_from(args):
    return dict(a.split("=", 1) for a in args)


def main(argv):
    cmd, rest = argv[0], argv[1:]
    if cmd == "validate":
        errs, warns = questions.validate(questions.read_questions(rest[0]))
        for w in warns:
            print("warning:", w)
        for e in errs:
            print("error:", e)
        return 1 if errs else 0
    if cmd == "retrieval":
        qs = questions.read_questions(rest[0])
        rows = []
        for label, run_dir in runs_from(rest[2:]).items():
            ret = [json.loads(l) for l in open(Path(run_dir) / "retrieval.jsonl")]
            rows += retrieval_score.score_run(qs, ret, label)
        retrieval_score.write_csv(rows, rest[1])
        return 0
    if cmd == "export":
        blind_export.export(runs_from(rest[3:]), questions.read_questions(rest[0]), rest[1], int(rest[2]))
        return 0
    if cmd == "join":
        d, out = Path(rest[0]), Path(rest[1])
        marked = marks.join_marks(marks.read_csv(d / "sheet_blind.csv"), marks.read_csv(d / "sheet_support.csv"), marks.read_csv(d / "key.csv"))
        out.mkdir(parents=True, exist_ok=True)
        marks.write_outcomes(marked, out / "outcomes_by_question.csv")
        for (config, cat), c in marks.counts(marked).items():
            print(f"{config}\t{cat}\t{c['yes']} of {c['N']} correct\t{c['partial']} partial")
        return 0
    if cmd == "score":
        qs = {q["id"]: q for q in questions.verified(questions.read_questions(rest[0]))}
        rows = []
        for label, run_dir in runs_from(rest[2:]).items():
            answers, retrieval, chunks = blind_export.load_run(run_dir)
            for a in answers:
                if a["question_id"] in qs:
                    context = " ".join(blind_export.context_texts(retrieval[a["question_id"]], chunks))
                    rows.append({"config_id": label, "question_id": a["question_id"], **rubric.score_answer(qs[a["question_id"]], a["answer"], context)})
        with open(rest[1], "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else [])
            w.writeheader()
            w.writerows(rows)
        return 0
    if cmd == "second-marker":
        ids = blind_export.second_marker_sample(rest[0], int(rest[1]) if len(rest) > 1 else 60, int(rest[2]) if len(rest) > 2 else 7)
        print(f"{len(ids)} answers written to {rest[0]}/sheet_second_marker.csv")
        return 0
    if cmd == "second-agreement":
        d = Path(rest[0])
        first = {r["answer_id"]: r for r in marks.read_csv(d / "sheet_blind.csv") if r["correct"].strip()}
        second = {r["answer_id"]: r for r in marks.read_csv(Path(rest[1])) if r["correct"].strip()}
        print(agreement.render_two_markers(agreement.two_markers(first, second)), end="")
        return 0
    if cmd == "analyze":
        import analysis
        analysis.run(rest[0], rest[1], rest[2])
        return 0
    if cmd == "agreement":
        d = Path(rest[0])
        key = marks.read_csv(d / "key.csv")
        person = {r["answer_id"]: r for r in marks.read_csv(d / "sheet_blind.csv") if r["correct"].strip()}
        support = {r["answer_id"]: r for r in marks.read_csv(d / "sheet_support.csv")}
        auto = {r["answer_id"]: r for r in marks.read_csv(d / "rubric_marks.csv")}
        pairs = []
        for aid, p in person.items():
            p = {**p, "unsupported_content": support.get(aid, {}).get("unsupported_content", "")}
            pairs.append((auto[aid], p))
        print(agreement.render(agreement.agreement(pairs)), end="")
        print(f"answers marked: {len(pairs)} of {len(auto)} shown; configurations behind them: {sum(1 for k in key if k['answer_id'] in person)}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
