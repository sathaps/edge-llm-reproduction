#!/usr/bin/env python3
"""Summarise probed manuals: pages, characters, applicability passages with page numbers, terms, keyword counts.

usage: manual_summary.py <manuals-dir> <out.csv>
Reads <dir>/<name>/provenance.json, pages/NNN.txt and applicability.txt written by manual_probe.py.
"""
import csv, glob, json, os, re, sys

KEYS = {"trip_shutdown": r"\b(trip|shut ?down|shutdown|alarm)\b", "setpoints_limits": r"\b(set ?point|setting|limit|maximum|minimum)\b",
        "pressure_test": r"pressure test|hydrostatic|leak test", "torque": r"\btorque\b", "numbered_steps": r"^\s*(?:step\s*)?\d{1,2}[.)]\s+\S",
        "prerequisite": r"\b(before you|prior to|make sure|ensure that|verify that)\b", "tables": r"^\s*table\s+\d+"}


def main(root, out_csv):
    rows = []
    for d in sorted(glob.glob(f"{root}/*/provenance.json")):
        name = os.path.basename(os.path.dirname(d))
        p = json.load(open(d))
        row = {"name": name, "url": p.get("source_url"), "is_pdf": p.get("is_pdf"), "pages": p.get("pages"), "chars": p.get("total_chars"),
               "sha256": (p.get("sha256") or "")[:16], "created": p.get("pdfinfo", {}).get("CreationDate", "")}
        if p.get("is_pdf"):
            text = "\n".join(open(f).read() for f in sorted(glob.glob(f"{os.path.dirname(d)}/pages/*.txt")))
            for k, rx in KEYS.items():
                row[k] = len(re.findall(rx, text, re.I | re.M))
            app = os.path.join(os.path.dirname(d), "applicability.txt")
            lines = open(app).read().splitlines() if os.path.exists(app) else []
            row["applicability_matches"] = len(lines)
            row["applicability_pages"] = ";".join(sorted({m.group(1) for l in lines for m in [re.match(r"\[pdf p(\d+)\]", l)] if m}, key=int)[:12])
            lic = os.path.join(os.path.dirname(d), "licence.txt")
            row["licence_lines"] = len(open(lic).read().splitlines()) if os.path.exists(lic) else 0
        rows.append(row)
    fields = sorted({k for r in rows for k in r}, key=lambda k: ["name", "url", "is_pdf", "pages", "chars"].index(k) if k in ("name", "url", "is_pdf", "pages", "chars") else 9)
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(json.dumps(r))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
