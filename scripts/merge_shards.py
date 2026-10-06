#!/usr/bin/env python3
"""Merge the shards of a cell into the layout of an unsharded run.

usage: merge_shards.py <results-dir>
Reads <dir>/shard-K-of-N/<cell>/rep-R/ for every shard of a cell and repeat, and writes <dir>/<cell>/rep-R/ with answers.jsonl,
retrieval.jsonl, stdout.txt, run.json and garbled.json. A cell with a missing shard is not merged and is named. run.json keeps
the first shard's values, adds "shards", and records in "shard_mismatch" any of commit, Ollama version, digests and PDF that
differ between shards. The question counts of garbled.json are summed. When an unsharded run of the same cell and
repeat exists, the merged shards go to <dir>/merged_shard_check/ and the unsharded run is left as it is.
"""
import json, re, sys
from collections import defaultdict
from pathlib import Path

SAME = ("commit", "ollama_version", "model_digest", "embedding_digest", "pdf_sha256")
SUM = ("questions", "retrieved_slots", "garbled_slots", "questions_with_a_garbled_chunk")


def merge(root):
    root = Path(root)
    groups = defaultdict(dict)
    totals = {}
    for d in sorted(root.glob("shard-*-of-*/*/rep-*")):
        m = re.match(r"shard-(\d+)-of-(\d+)", d.parent.parent.name)
        groups[(d.parent.name, d.name)][int(m.group(1))] = d
        totals[(d.parent.name, d.name)] = int(m.group(2))
    done, missing = [], []
    for (cell, rep), shards in sorted(groups.items()):
        n = totals[(cell, rep)]
        if sorted(shards) != list(range(1, n + 1)) or not all((s / "answers.jsonl").exists() for s in shards.values()):
            missing.append(f"{cell}/{rep}: shards {sorted(shards)} of {n}")
            continue
        out = root / cell / rep
        if (out / "run.json").exists() and "shards" not in json.load(open(out / "run.json")):
            out = root / "merged_shard_check" / cell / rep  # an unsharded run of the same cell and repeat stays the run of record
        out.mkdir(parents=True, exist_ok=True)
        ordered = [shards[k] for k in range(1, n + 1)]
        for name in ("answers.jsonl", "retrieval.jsonl", "stdout.txt"):
            with open(out / name, "w") as f:
                for s in ordered:
                    if (s / name).exists():
                        text = (s / name).read_text()
                        f.write(text if text.endswith("\n") or not text else text + "\n")
        runs = [json.load(open(s / "run.json")) for s in ordered]
        run = dict(runs[0])
        run["shards"] = n
        run["shard_mismatch"] = {k: [r.get(k) for r in runs] for k in SAME if len({str(r.get(k)) for r in runs}) > 1}
        json.dump(run, open(out / "run.json", "w"), indent=1)
        gs = [json.load(open(s / "garbled.json")) for s in ordered if (s / "garbled.json").exists()]
        if gs:
            g = dict(gs[0])
            for k in SUM:
                if k in g:
                    g[k] = sum(x.get(k, 0) for x in gs)
            json.dump(g, open(out / "garbled.json", "w"), indent=1)
        done.append(f"{cell}/{rep}: {n} shards")
    return done, missing


if __name__ == "__main__":
    done, missing = merge(sys.argv[1])
    print("\n".join("merged " + d for d in done))
    print("\n".join("NOT merged " + m for m in missing))
    sys.exit(1 if missing else 0)
