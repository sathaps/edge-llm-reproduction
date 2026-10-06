#!/usr/bin/env bash
# Freeze the protocol: check that the question set is verified, write the manifest, commit and tag.
# usage: scripts/freeze.sh protocol-v1
# Run it once the maintainer's corrections are merged. It refuses to freeze with an unverified question.
set -euo pipefail
tag="$1"
python3 scoring/run_scoring.py validate questions/questions.csv
python3 scoring/run_scoring.py validate questions/cummins_cfp11e_unreadable.csv --no-minimums
python3 scoring/run_scoring.py selfcheck questions/questions.csv
python3 scoring/run_scoring.py selfcheck questions/cummins_cfp11e_unreadable.csv
python3 - <<'PY'
import csv, sys
rows = list(csv.DictReader(open("questions/questions.csv")))
open_rows = [r["id"] for r in rows if not (r["verified_by"] or "").strip()]
if open_rows:
    sys.exit(f"unverified questions: {open_rows}")
print(f"{len(rows)} questions, all verified")
PY
python3 -m pytest -q tests
python3 scripts/freeze_manifest.py write "$tag.manifest"
git add "$tag.manifest"
git commit -m "Freeze the question set, the scorer, the marking rules and the planned comparisons ($tag)"
git tag "$tag"
echo "tagged $tag; push with: git push origin main $tag"
