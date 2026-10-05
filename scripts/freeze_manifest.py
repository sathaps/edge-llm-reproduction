#!/usr/bin/env python3
"""Write or check the manifest of frozen files.

usage: freeze_manifest.py write <manifest> | check <manifest>
The frozen files are the question set, the scorer, the marking rules, the planned comparisons, the E1 cells and the
pipeline settings. `check` exits 1 and names every file that differs from the manifest or is missing.
"""
import hashlib, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FROZEN = ["questions/questions.csv", "experiments/comparisons.json", "experiments/e1.json", "config/pipelines.json",
          "scoring/MARKING_RULES.md", "scoring/rubric.py", "scoring/questions.py", "scoring/agreement.py", "scoring/analysis.py",
          "scoring/blind_export.py", "scoring/marks.py", "scoring/summary_tables.py", "scoring/retrieval_score.py", "scoring/run_scoring.py"]


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def write(manifest):
    Path(manifest).write_text("".join(f"{digest(f)}  {f}\n" for f in FROZEN))


def check(manifest):
    bad = []
    for line in Path(manifest).read_text().splitlines():
        want, name = line.split("  ", 1)
        if not (ROOT / name).exists():
            bad.append(f"{name}: missing")
        elif digest(name) != want:
            bad.append(f"{name}: changed")
    return bad


if __name__ == "__main__":
    if sys.argv[1] == "write":
        write(sys.argv[2])
    else:
        problems = check(sys.argv[2])
        print("\n".join(problems) or "frozen files unchanged")
        sys.exit(1 if problems else 0)
