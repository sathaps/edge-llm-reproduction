#!/usr/bin/env python3
"""Merge the maintainer's verification of a pack into the question files.

usage: merge_verification.py <delivered.csv> <returned.xlsx|csv> <main.csv> <unreadable.csv> --by NAME --on DATE
`delivered` is the pack as it was handed over. A cell the maintainer changed in the returned file is a correction and
replaces the value in the question file. A cell he left alone keeps the value in the question file, which may have been
corrected since delivery. The verdict column: ok marks the row verified; fix marks it verified only when the row has
cell changes (a fix with no changed cell is listed as unresolved); drop removes the row; an empty verdict leaves it
unverified. Prints a report and writes both question files. Exit status 1 when anything is unresolved.
"""
import csv, sys
from pathlib import Path

EDITABLE = ["question", "reference_answer", "source_pages", "exclusion_pages", "required_elements", "forbidden_elements"]


def read_any(path):
    if str(path).endswith(".xlsx"):
        from openpyxl import load_workbook
        ws = load_workbook(path, data_only=True).active
        rows = list(ws.iter_rows(values_only=True))
        head = [str(h) for h in rows[0]]
        return [{h: ("" if v is None else str(v)) for h, v in zip(head, r)} for r in rows[1:] if r and r[0]]
    return list(csv.DictReader(open(path, newline="")))


def write(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def merge(delivered, returned, main, unreadable, by, on):
    sent = {r["id"]: r for r in delivered}
    files = {"main": main, "unreadable": unreadable}
    report = {"verified": [], "corrected": {}, "dropped": [], "unverified": [], "unresolved": [], "unknown": []}
    for r in returned:
        qid = r["id"]
        if qid not in sent:
            report["unknown"].append(qid)
            continue
        target = {q["id"]: q for q in files.get(sent[qid].get("set", "main"), main)}
        q = target.get(qid)
        if q is None:
            report["unknown"].append(qid)
            continue
        changed = [c for c in EDITABLE if (r.get(c) or "").strip() != (sent[qid].get(c) or "").strip()]
        for c in changed:
            q[c] = r[c].strip()
        if changed:
            report["corrected"][qid] = changed
        verdict = (r.get("verdict") or "").strip().lower()
        if verdict == "drop":
            q["_drop"] = True
            report["dropped"].append(qid)
        elif verdict == "ok" or (verdict == "fix" and changed):
            q["verified_by"], q["verified_on"] = by, on
            report["verified"].append(qid)
        elif verdict == "fix":
            report["unresolved"].append(f"{qid}: verdict fix without a changed cell; correction note: {(r.get('correction') or '').strip()[:120]}")
        else:
            report["unverified"].append(qid)
    return report


def main(argv):
    delivered, returned, main_csv, unread_csv = argv[:4]
    by, on = argv[argv.index("--by") + 1], argv[argv.index("--on") + 1]
    main_rows, unread_rows = read_any(main_csv), read_any(unread_csv)
    fields = list(main_rows[0])
    report = merge(read_any(delivered), read_any(returned), main_rows, unread_rows, by, on)
    for path, rows in ((main_csv, main_rows), (unread_csv, unread_rows)):
        write(path, [{k: v for k, v in q.items() if k != "_drop"} for q in rows if not q.get("_drop")], fields)
    for k, v in report.items():
        print(f"{k}: {len(v)}", dict(v) if isinstance(v, dict) else v)
    return 1 if report["unresolved"] or report["unknown"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
