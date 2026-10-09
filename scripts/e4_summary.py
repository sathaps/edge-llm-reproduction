#!/usr/bin/env python3
"""E4: resource use per cell from the per-job resources files of a collected experiment.

usage: e4_summary.py <results-dir> <prefix, for example e1> [out.md]
Each job wrote a resources file; the collect step stored it as resources-<prefix>-<cell>-rep<N>[-s<K>].csv, sometimes together
with older files that the job's checkout carried along. A row counts only when its cell and repeat match the file name.
For a sharded cell the shards are combined: the peak memory is the largest peak, the time per answer is weighted by the
answers of each shard, the index time is the mean over the shards (each builds its own index) and the wall time is the sum.
The table gives, per cell, the mean over the repeats with the smallest and largest value in brackets. Runner measurements:
4 CPUs, 15 GB, CPU only, one job at a time on the runner.
"""
import csv, re, sys
from collections import defaultdict
from pathlib import Path


def load(root, prefix):
    seen, jobs = set(), defaultdict(list)
    for f in sorted(Path(root).rglob(f"resources-{prefix}-*.csv")):
        m = re.fullmatch(rf"resources-{prefix}-(.+)-rep(\d+)(?:-s(\d+))?\.csv", f.name)
        if not m:
            continue
        cell, rep, shard = m.group(1), int(m.group(2)), int(m.group(3) or 1)
        for r in csv.DictReader(open(f)):
            if r["cell"] == cell and int(r["rep"]) == rep and (cell, rep, shard) not in seen:
                seen.add((cell, rep, shard))
                jobs[(cell, rep)].append(r)
    return jobs


def combine(rows):
    n = sum(int(r["answers"]) for r in rows)
    return {"pipeline_mb": max(float(r["pipeline_peak_rss_kb"]) for r in rows) / 1024,
            "ollama_gb": max(float(r["ollama_peak_rss_kb"]) for r in rows) / 1048576,
            "index_s": sum(float(r["index_build_s"] or 0) for r in rows) / len(rows),
            "index_kb": float(rows[0]["index_bytes"] or 0) / 1024,
            "s_per_answer": sum(float(r["mean_answer_s"]) * int(r["answers"]) for r in rows) / n,
            "wall_h": sum(float(r["wall_s"]) for r in rows) / 3600, "jobs": len(rows), "answers": n}


def render(jobs):
    cells = sorted({c for c, _ in jobs})
    head = ("| Cell | Repeats | Jobs per repeat | Peak memory, pipeline (MB) | Peak memory, Ollama (GB) | Index build (s) | Index size (KB) | Time per answer (s) | Job time, summed over shards (h) |\n"
            "|---|---|---|---|---|---|---|---|---|\n")
    lines = []
    for c in cells:
        per = [combine(jobs[(c, r)]) for r in sorted(r for cc, r in jobs if cc == c)]

        def span(k, fmt):
            v = [p[k] for p in per]
            return f"{fmt % (sum(v) / len(v))} ({fmt % min(v)}-{fmt % max(v)})"

        lines.append(f"| {c} | {len(per)} | {per[0]['jobs']} | {span('pipeline_mb', '%.0f')} | {span('ollama_gb', '%.1f')} | {span('index_s', '%.1f')} | {span('index_kb', '%.0f')} | {span('s_per_answer', '%.1f')} | {span('wall_h', '%.2f')} |")
    return head + "\n".join(lines) + "\n"


if __name__ == "__main__":
    jobs = load(sys.argv[1], sys.argv[2])
    text = render(jobs)
    print(text)
    if len(sys.argv) > 3:
        open(sys.argv[3], "w").write(text)
