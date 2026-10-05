#!/usr/bin/env python3
"""Check that every section of results/summary.md with a table names its runs and commit, and that the index lists it.

usage: check_index.py [results-dir]
A section is a `## ` heading up to the next one. A section with a table row must contain a `Source:` line with an
`Index entry:` or a `run` and `commit`, and every `Index entry:` name must be in results/index.md.
"""
import re, sys
from pathlib import Path


def problems(results_dir):
    summary = (Path(results_dir) / "summary.md").read_text()
    index = (Path(results_dir) / "index.md").read_text()
    out = []
    for section in re.split(r"^## ", summary, flags=re.M)[1:]:
        title = section.splitlines()[0]
        if not re.search(r"^\|", section, flags=re.M):
            continue
        source = re.search(r"^Source:.*$", section, flags=re.M)
        if not source or "commit" not in source.group(0) or "run" not in source.group(0).lower():
            out.append(f"{title}: table without a Source line that names run and commit")
            continue
        for entry in re.findall(r"Index entry: `([^`]+)`", section):
            if f"`{entry}`" not in index:
                out.append(f"{title}: index entry {entry} is not in index.md")
    return out


if __name__ == "__main__":
    found = problems(sys.argv[1] if len(sys.argv) > 1 else "results")
    print("\n".join(found) or "ok")
    sys.exit(1 if found else 0)
