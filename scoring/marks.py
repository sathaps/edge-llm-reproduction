import csv
from collections import OrderedDict



def read_csv(path):
    return list(csv.DictReader(open(path, newline="")))


def join_marks(sheet_blind, sheet_support, key):
    """Join the marked sheets to the key. Rows with an empty correct mark are not yet marked and are left out."""
    support = {r["answer_id"]: r for r in sheet_support}
    keys = {r["answer_id"]: r for r in key}
    out = []
    for r in sheet_blind:
        if not r["correct"].strip():
            continue
        k = keys[r["answer_id"]]
        out.append({"answer_id": r["answer_id"], "config_id": k["config_id"], "question_id": k["question_id"],
                    "category": r["category"], "correct": r["correct"].strip().lower(),
                    "complete": r["complete"].strip().lower(), "respects_applicability": r["respects_applicability"].strip().lower(),
                    "abstained": r["abstained"].strip().lower(),
                    "unsupported_content": support.get(r["answer_id"], {}).get("unsupported_content", "").strip().lower()})
    return out


def counts(marked):
    """n of N correct per configuration and category."""
    table = OrderedDict()
    for r in marked:
        c = table.setdefault((r["config_id"], r["category"]), {"N": 0, "yes": 0, "partial": 0})
        c["N"] += 1
        c["yes"] += r["correct"] == "yes"
        c["partial"] += r["correct"] == "partial"
    return table


def outcomes_by_question(marked):
    """Question by configuration table of the correct mark, so paired comparisons can be read off."""
    configs = sorted({r["config_id"] for r in marked})
    rows = OrderedDict()
    for r in marked:
        rows.setdefault(r["question_id"], {"question_id": r["question_id"], "category": r["category"]})[r["config_id"]] = r["correct"]
    return configs, [{**row, **{c: row.get(c, "") for c in configs}} for row in rows.values()]


def write_outcomes(marked, path):
    configs, rows = outcomes_by_question(marked)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["question_id", "category"] + configs)
        w.writeheader()
        w.writerows(rows)
