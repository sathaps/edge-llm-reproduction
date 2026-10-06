#!/usr/bin/env python3
"""Table of the E1 cells with the software each ran on: commit, Ollama version, model and embedding digests.

usage: e1_table.py <results/e1> [expected-commit ...]
Reads <dir>/<cell>/rep-N/run.json. Prints a markdown table and a line that says whether the Ollama version and the
digests are the same in every cell. Exit status 1 when they differ, so a rerun on different software is not used silently.
"""
import json, sys
from pathlib import Path


def rows(root):
    out = []
    for p in sorted(Path(root).glob("*/rep-*/run.json")):
        r = json.load(open(p))
        out.append({"cell": p.parent.parent.name, "rep": p.parent.name.split("-")[1], "commit": (r.get("commit") or "")[:7],
                    "ollama": r.get("ollama_version"), "model": r.get("model"), "model_digest": (r.get("model_digest") or "")[:12],
                    "embedding_digest": (r.get("embedding_digest") or "")[:12], "pdf_sha256": (r.get("pdf_sha256") or "")[:12]})
    return out


def render(table):
    head = "| Cell | Rep | Commit | Ollama | Model | Model digest | Embedding digest | PDF SHA-256 |\n|---|---|---|---|---|---|---|---|\n"
    return head + "".join(f"| {r['cell']} | {r['rep']} | {r['commit']} | {r['ollama']} | {r['model']} | {r['model_digest']} | {r['embedding_digest']} | {r['pdf_sha256']} |\n" for r in table)


def differences(table):
    """What differs between cells: the Ollama version, the digest of a model that two cells share, the PDF."""
    notes = []
    for key in ("ollama", "pdf_sha256"):
        values = {r[key] for r in table}
        if len(values) > 1:
            notes.append(f"{key} differs: {sorted(map(str, values))}")
    for key in ("model_digest", "embedding_digest"):
        by_model = {}
        for r in table:
            by_model.setdefault(r["model"] if key == "model_digest" else ("emb-" + r["embedding_digest"][:0] + r["cell"][0]), set()).add(r[key])
        for m, v in by_model.items():
            if len(v) > 1:
                notes.append(f"{key} of {m} differs: {sorted(v)}")
    return notes


if __name__ == "__main__":
    t = rows(sys.argv[1])
    print(render(t))
    d = differences(t)
    print("; ".join(d) if d else "Ollama version, model digests and PDF are the same in every cell.")
    sys.exit(1 if d else 0)
