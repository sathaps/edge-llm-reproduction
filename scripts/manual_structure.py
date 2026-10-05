#!/usr/bin/env python3
"""Map the structure of a manual from its per-page text: procedures, tables, limits and applicability passages.

usage: manual_structure.py <pages-dir> <out-dir> [--text]
Output has page numbers and counts only. With --text a short label (the text of the first line, at most 12 words) is
added for local use. Procedures are runs of step numbers 1, 2, 3 ... found in page order, so the count is approximate on
pages with two columns. A run crosses a page boundary when it starts and ends on different pages.
"""
import csv, glob, os, re, sys

STEP = re.compile(r"(?:^|\s{3,})(\d{1,2})[.)]\s+(?=[A-Z])", re.M)
PREREQ = re.compile(r"\b(before|prior to|make sure|ensure|verify|must be|only after)\b", re.I)
WARN = re.compile(r"\b(warning|caution|danger)\b", re.I)
TABLE = re.compile(r"^\s*(table\s+\d+[-.\d]*)", re.I | re.M)
LIMIT_WORDS = re.compile(r"\b(trip|shut ?down|alarm|maximum|minimum|max\.?|min\.?|limit|set ?point|setting|threshold)\b", re.I)
VALUE = re.compile(r"\d+(\.\d+)?\s?(psi|kpa|bar|°\s?[CF]|rpm|v|vdc|vac|a|amps?|hz|%|mm|in|ft|lb|n·?m|gpm|l/min)\b", re.I)
APPLIES = re.compile(r"(applies?\s+(only\s+)?to|applicable\s+(only\s+)?to|not\s+applicable|does\s+not\s+apply|not\s+available|only\s+(on|for|with)|(models?|engines?)\s+only|on\s+\w+\s+(models?|engines?)\s+only)", re.I)


def pages(pages_dir):
    return [(int(os.path.basename(p).split(".")[0]), open(p, errors="replace").read()) for p in sorted(glob.glob(f"{pages_dir}/*.txt"))]


def procedures(pp):
    """Runs of consecutive step numbers. Returns dicts with start_page, end_page, steps, crosses_page, prerequisite_words, warnings."""
    runs, cur = [], None
    for page, text in pp:
        for m in STEP.finditer(text):
            n = int(m.group(1))
            if cur and n == cur["last"] + 1 and page - cur["end"] <= 1:
                cur.update(last=n, end=page, steps=cur["steps"] + 1)
            else:
                if cur and cur["steps"] >= 3:
                    runs.append(cur)
                cur = {"start": page, "end": page, "last": n, "steps": 1} if n == 1 else None
        if cur:
            cur["text"] = cur.get("text", "") + text
    if cur and cur["steps"] >= 3:
        runs.append(cur)
    out = []
    for i, r in enumerate(runs, 1):
        text = r.pop("text", "")
        before = text[:text.find("1.")] if "1." in text else ""
        out.append({"procedure": f"proc-{i:03d}", "start_page": r["start"], "end_page": r["end"], "steps": r["steps"],
                    "crosses_page": r["start"] != r["end"], "prerequisite_words": len(PREREQ.findall(before[-600:])), "warnings": len(WARN.findall(text))})
    return out


def tables(pp):
    out = []
    for page, text in pp:
        for m in TABLE.finditer(text):
            block = text[m.start():m.start() + 3500]
            out.append({"page": page, "label": m.group(1), "limit_words": len(LIMIT_WORDS.findall(block)), "value_cells": len(VALUE.findall(block))})
    return out


def limits(pp):
    out = []
    for page, text in pp:
        lines = [l for l in text.splitlines() if LIMIT_WORDS.search(l) and VALUE.search(l)]
        trip = [l for l in lines if re.search(r"trip|shut ?down|alarm", l, re.I)]
        if lines:
            out.append({"page": page, "limit_lines": len(lines), "trip_or_alarm_lines": len(trip)})
    return out


def applicability(pp, with_text=False):
    out = []
    for page, text in pp:
        hits = APPLIES.findall(text)
        if hits:
            row = {"page": page, "matches": len(hits)}
            if with_text:
                m = APPLIES.search(text)
                row["label"] = " ".join(text[max(0, m.start() - 60):m.end() + 80].split()[:12])
            out.append(row)
    return out


def write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["none"])
        w.writeheader()
        w.writerows(rows)


def main(pages_dir, out_dir, with_text=False):
    os.makedirs(out_dir, exist_ok=True)
    pp = pages(pages_dir)
    result = {"procedures": procedures(pp), "tables": tables(pp), "limits": limits(pp), "applicability": applicability(pp, with_text)}
    for name, rows in result.items():
        write(f"{out_dir}/{name}.csv", rows)
    procs = result["procedures"]
    print(f"pages {len(pp)}; procedures {len(procs)} of which {sum(p['crosses_page'] for p in procs)} cross a page boundary; "
          f"steps in procedures {sum(p['steps'] for p in procs)}; procedures with prerequisite words {sum(p['prerequisite_words'] > 0 for p in procs)}")
    print(f"tables {len(result['tables'])} on {len({t['page'] for t in result['tables']})} pages; tables with limit words {sum(t['limit_words'] > 0 for t in result['tables'])}")
    print(f"pages with limit lines {len(result['limits'])}; pages with trip or alarm lines {sum(l['trip_or_alarm_lines'] > 0 for l in result['limits'])}")
    print(f"pages with applicability phrases {len(result['applicability'])}; matches {sum(a['matches'] for a in result['applicability'])}")
    return result


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--text" in sys.argv)
