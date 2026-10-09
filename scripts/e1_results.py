#!/usr/bin/env python3
"""Unblind the marked E1 repeat 1 sheet and compute the planned counts, comparisons and scorer agreement.

usage: e1_results.py <marks.csv from marking_sheet.py check --emit> <key.csv> <out-dir>
Reads results/e1 (repeat 1 answers, for the automatic scorer) and results/e2 (repeat 1 answers of the E2 cells). A mark on an
answer that several cells gave applies to every one of those cells. The note column is never read into any output.
Writes into <out-dir>: marks_rep1.csv (by answer id, no key), marks_rep1_by_cell.csv, rep1_counts.md, rep1_comparisons.csv
(and _with_partial), rep1_scorer_agreement.md, outcomes_by_question.csv.
unsupported_content is not marked and is not computed here. The scorer is run without the retrieved text.
"""
import csv, json, sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scoring")); sys.path.insert(0, str(ROOT / "scripts"))
import agreement, analysis, marks, questions as qmod, rubric  # noqa: E402
import auto_score  # noqa: E402

FIELDS = ["correct", "complete", "respects_applicability", "abstained"]
CATS = list(qmod.MINIMUM)
CELLS = ["A-llama3", "A-mistral", "A-tinyllama", "B-llama3", "B-mistral", "B-tinyllama"]


def pct(x):
    return "n/a" if x is None else f"{100 * x:.0f}"


def cell_text(k, n):
    lo, hi = analysis.wilson(k, n)
    return f"{k} of {n} ({pct(lo)}-{pct(hi)} %)"


def main(marks_csv, key_csv, out_dir):
    out = Path(out_dir)
    emit = list(csv.DictReader(open(marks_csv, newline="")))
    key = marks.read_csv(key_csv)
    joined = marks.join_marks(emit, [], key)  # one row per cell behind each marked answer
    qs = {q["id"]: q for q in qmod.verified(qmod.read_questions(ROOT / "questions" / "questions.csv"))}
    order = list(qs)
    with open(out / "marks_rep1.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["answer_id", "category"] + FIELDS)
        for r in emit:  # no note column
            w.writerow([r["answer_id"], r["category"]] + [r[c] for c in FIELDS])
    byc = sorted(joined, key=lambda r: (r["config_id"], order.index(r["question_id"])))
    with open(out / "marks_rep1_by_cell.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cell", "question_id", "category", "answer_id"] + FIELDS)
        for r in byc:
            w.writerow([r["config_id"], r["question_id"], r["category"], r["answer_id"]] + [r[c] for c in FIELDS])
    assert len(byc) == 240 and all(sum(1 for r in byc if r["config_id"] == c) == 40 for c in CELLS)
    marks.write_outcomes(joined, out / "outcomes_by_question.csv")

    # counts with Wilson intervals
    lines = ["# E1 repeat 1: maintainer's marks, n of N with Wilson 95 % intervals", "",
             "Source: marked sheet checked with `scripts/marking_sheet.py check`; unblinded with the key whose SHA-256 was recorded before marking. Each cell has 40 answers (8 per category). A mark on an answer that several cells gave counts for each of them. `unsupported_content` is not marked.", ""]
    lines += ["## All 40 questions", "", "| Cell | correct: yes | correct: partial | correct: no | complete: yes | abstained: yes |", "|---|---|---|---|---|---|"]
    for c in CELLS:
        rows = [r for r in joined if r["config_id"] == c]
        n = len(rows)
        cnt = lambda f, v: sum(r[f] == v for r in rows)
        lines.append(f"| {c} | {cell_text(cnt('correct','yes'), n)} | {cell_text(cnt('correct','partial'), n)} | {cell_text(cnt('correct','no'), n)} | {cell_text(cnt('complete','yes'), n)} | {cell_text(cnt('abstained','yes'), n)} |")
    for field, value, title in (("correct", "yes", "correct: yes"), ("correct", "partial", "correct: partial"), ("complete", "yes", "complete: yes"), ("abstained", "yes", "abstained: yes")):
        lines += ["", f"## Per category: {title}", "", "| Cell | " + " | ".join(CATS) + " |", "|---|" + "---|" * len(CATS)]
        for c in CELLS:
            cols = []
            for cat in CATS:
                rows = [r for r in joined if r["config_id"] == c and r["category"] == cat]
                cols.append(cell_text(sum(r[field] == value for r in rows), len(rows)))
            lines.append(f"| {c} | " + " | ".join(cols) + " |")
    lines += ["", "## respects_applicability: yes (applicability questions only)", "", "| Cell | respects_applicability: yes |", "|---|---|"]
    for c in CELLS:
        rows = [r for r in joined if r["config_id"] == c and r["category"] == "applicability"]
        lines.append(f"| {c} | {cell_text(sum(r['respects_applicability'] == 'yes' for r in rows), len(rows))} |")
    (out / "rep1_counts.md").write_text("\n".join(lines) + "\n")

    # automatic scorer on E1 repeat 1 and E2 repeat 1 (no retrieved text)
    e1_auto = auto_score.score(ROOT / "questions" / "questions.csv", ROOT / "results" / "e1", [1])
    e2_auto = auto_score.score(ROOT / "questions" / "questions.csv", ROOT / "results" / "e2", [1])
    rows = [{"config_id": f"{r['config_id']}@1", "question_id": r["question_id"], "outcome": r["correct"]} for r in joined]  # marks
    rows += [{"config_id": f"{r['cell']}@1", "question_id": r["question_id"], "outcome": r["correct"]} for r in e2_auto]
    rows += [{"config_id": f"{r['cell']}-auto@1", "question_id": r["question_id"], "outcome": r["correct"]} for r in e1_auto if r["cell"] == "B-llama3"]
    comps = json.load(open(ROOT / "experiments" / "comparisons.json"))["comparisons"]
    comps += json.load(open(ROOT / "experiments" / "comparisons_amendment.json"))["comparisons"]
    comps = [dict(c, a="B-llama3-auto", rep=1) if c["id"] == "P17" else dict(c, rep=1) for c in comps]
    for name, partial in (("", False), ("_with_partial", True)):
        res = analysis.run_comparisons(rows, comps, partial)
        for r in res:
            r["data"] = "maintainer's marks" if r["id"] in ("P1", "P2", "P3") else "automatic scorer only"
        analysis.write_csv(out / f"rep1_comparisons{name}.csv", res)

    # agreement of the automatic scorer with the maintainer, per distinct answer
    answers = {}
    for r in key:
        pass
    by_ans = OrderedDict()
    for k in key:
        by_ans.setdefault(k["answer_id"], k)
    ans_text = {}
    for cell in CELLS:
        for line in open(ROOT / "results" / "e1" / cell / "rep-1" / "answers.jsonl"):
            a = json.loads(line)
            ans_text[(cell, a["question_id"])] = a["answer"]
    pairs, labels = [], {c: [] for c in FIELDS}
    for e in emit:
        k = by_ans[e["answer_id"]]
        text = ans_text[(k["config_id"], k["question_id"])]
        auto = rubric.score_answer(qs[k["question_id"]], text, "")
        pairs.append((auto, e))
        for c in FIELDS:
            labels[c].append((auto.get(c, ""), e.get(c, "")))
    ag = agreement.agreement([({c: a[c] for c in FIELDS}, {c: p[c] for c in FIELDS}) for a, p in pairs])
    md = ["# E1 repeat 1: agreement of the automatic scorer with the maintainer's marks", "",
          "Unit: the 237 distinct answers. The scorer ran without the retrieved text. `unsupported_content` is not marked and is not compared. Same mark = identical value. Kappa is Cohen's kappa over the values present.", "",
          "| Field | Same mark | Same on yes versus not yes | Cohen's kappa | N |", "|---|---|---|---|---|"]
    for c in FIELDS:
        kappa, n, agree = agreement.cohen_kappa(labels[c])
        md.append(f"| {c} | {agree} of {n} | {ag[c]['agree_yes_vs_not_yes']} of {n} | {'n/a' if kappa is None else f'{kappa:.3f}'} | {n} |")
    # confusion for correct
    conf = OrderedDict()
    for a, p in labels["correct"]:
        conf[(a, p)] = conf.get((a, p), 0) + 1
    md += ["", "Scorer against maintainer for `correct` (rows scorer, columns maintainer):", "", "| scorer \\ maintainer | yes | partial | no |", "|---|---|---|---|"]
    for a in ("yes", "partial", "no"):
        md.append(f"| {a} | " + " | ".join(str(conf.get((a, p), 0)) for p in ("yes", "partial", "no")) + " |")
    (out / "rep1_scorer_agreement.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(*sys.argv[1:4])
