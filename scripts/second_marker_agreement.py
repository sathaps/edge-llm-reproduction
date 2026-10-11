#!/usr/bin/env python3
"""Agreement between the first marker and a second marker on a sample, per field.

usage: second_marker_agreement.py <second marker's marked.xlsx> <first marker's marks_rep1.csv> <out-dir> [label]
The second marker's file is read as it was returned; nothing in it is filled or changed. An empty cell is not a mark and the
answer is left out of that field only. Writes second_marker_<label>_marks.csv (answer id, category and the four fields, no
notes) and second_marker_<label>_agreement.md (counts, Cohen's kappa, the 3 by 3 table for `correct`, `correct` as yes versus
not yes). The note column is never read.
"""
import csv, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scoring")); sys.path.insert(0, str(ROOT / "scripts"))
import agreement, marking_sheet as ms  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

FIELDS = list(ms.MARKS)


def main(marked, first_csv, out_dir, label="D"):
    second = {}
    for r in ms.read_tab(load_workbook(marked)["Answers"])[1]:
        second[str(r["answer_id"])] = {"category": r["category"], **{c: ("" if r[c] is None else str(r[c]).strip().lower()) for c in FIELDS}}
    first = {r["answer_id"]: r for r in csv.DictReader(open(first_csv, newline=""))}
    assert set(second) <= set(first), "answer ids that the first marker never marked"
    out = Path(out_dir)
    with open(out / f"second_marker_{label}_marks.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["answer_id", "category"] + FIELDS)
        for aid, r in second.items():
            w.writerow([aid, r["category"]] + [r[c] for c in FIELDS])
    lines = [f"# Second marker, sample {label}: agreement with the first marker", "",
             f"{len(second)} distinct answers. An empty cell is not a mark; the answer is left out of that field only.", "",
             "| Field | Answers compared | Same mark | Cohen's kappa |", "|---|---|---|---|"]
    detail = {}
    for c in FIELDS:
        pairs = [(first[a][c], second[a][c]) for a in second if first[a][c].strip() and second[a][c]]
        kappa, n, agree = agreement.cohen_kappa(pairs)
        detail[c] = pairs
        lines.append(f"| {c} | {n} | {agree} of {n} | {'n/a' if kappa is None else f'{kappa:.3f}'} |")
    pairs = detail["correct"]
    binp = [("yes" if a == "yes" else "not yes", "yes" if b == "yes" else "not yes") for a, b in pairs]
    k, n, agree = agreement.cohen_kappa(binp)
    lines += ["", f"`correct` as yes versus not yes: {agree} of {n} agree, Cohen's kappa {k:.3f}.", "",
              "`correct`, rows first marker, columns second marker:", "", "| first \\ second | yes | partial | no |", "|---|---|---|---|"]
    cnt = Counter(pairs)
    for a in ("yes", "partial", "no"):
        lines.append(f"| {a} | " + " | ".join(str(cnt[(a, b)]) for b in ("yes", "partial", "no")) + " |")
    for c in ("complete", "abstained", "respects_applicability"):
        cnt = Counter(detail[c])
        vals = ("yes", "no")
        lines += ["", f"`{c}`, rows first marker, columns second marker:", "", "| first \\ second | yes | no |", "|---|---|---|"]
        for a in vals:
            lines.append(f"| {a} | " + " | ".join(str(cnt[(a, b)]) for b in vals) + " |")
    left_out = {c: sum(1 for a in second if not second[a][c] and first[a][c].strip()) for c in FIELDS}
    lines += ["", "Answers left out because the second marker's cell is empty: " + ", ".join(f"{c} {v}" for c, v in left_out.items() if v) + "."]
    text = "\n".join(lines) + "\n"
    (out / f"second_marker_{label}_agreement.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main(*sys.argv[1:5])
