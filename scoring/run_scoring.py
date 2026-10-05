#!/usr/bin/env python3
"""Command line for the scoring steps.

  run_scoring.py validate questions/questions.csv
  run_scoring.py retrieval questions/questions.csv OUT.csv LABEL=RUN_DIR [LABEL=RUN_DIR ...]
  run_scoring.py export questions/questions.csv OUT_DIR SEED LABEL=RUN_DIR [LABEL=RUN_DIR ...]
  run_scoring.py join MARKING_DIR OUT_DIR
"""
import json
import sys
from pathlib import Path

import blind_export, marks, questions, retrieval_score


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
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
