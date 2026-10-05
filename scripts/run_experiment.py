#!/usr/bin/env python3
"""Run the cells of an experiment, each repeated, and record peak memory per run.

usage: run_experiment.py experiments/e1.json --pdf MANUAL.pdf --out results/e1 [--ollama URL] [--questions CSV] [--cell ID ...] [--rep N ...]

An experiment file lists cells: {"id", "impl": "a"|"b", "model", "set": ["path=value", ...], "conversation"}.
Output: <out>/env.txt, <out>/<cell>/rep-N/ (the pipeline's files) and <out>/resources.csv.
"""
import argparse, csv, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLLAMA_COMM = ("ollama", "llama-server", "ollama_llama")


def status_kb(pid, field):
    try:
        for line in open(f"/proc/{pid}/status"):
            if line.startswith(field + ":"):
                return int(line.split()[1])
    except OSError:
        pass
    return 0


def descendants(pid, table):
    out, stack = [], [pid]
    while stack:
        p = stack.pop()
        out.append(p)
        stack += [c for c, parent in table.items() if parent == p]
    return out


def process_table():
    table = {}
    for d in os.listdir("/proc"):
        if d.isdigit():
            try:
                table[int(d)] = int(open(f"/proc/{d}/stat").read().rsplit(")", 1)[1].split()[1])
            except (OSError, IndexError, ValueError):
                pass
    return table


def ollama_pids():
    pids = []
    for d in os.listdir("/proc"):
        if d.isdigit():
            try:
                if open(f"/proc/{d}/comm").read().strip().startswith(OLLAMA_COMM):
                    pids.append(int(d))
            except OSError:
                pass
    return pids


def run_sampled(cmd, interval=0.1, **kw):
    """Run cmd and return (returncode, wall seconds, peak RSS kB of its process tree, peak RSS kB of the Ollama processes)."""
    t0 = time.time()
    proc = subprocess.Popen(cmd, **kw)
    pipe_peak = ollama_peak = 0
    while proc.poll() is None:
        table = process_table()
        tree = descendants(proc.pid, table)
        pipe_peak = max(pipe_peak, sum(status_kb(p, "VmRSS") for p in tree), status_kb(proc.pid, "VmHWM"))
        ollama_peak = max(ollama_peak, sum(status_kb(p, "VmRSS") for p in ollama_pids()))
        time.sleep(interval)
    return proc.returncode, time.time() - t0, pipe_peak, ollama_peak


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()


def write_env(out, ollama):
    version = sh(f"curl -s {ollama}/api/version")
    tags = sh(f"curl -s {ollama}/api/tags")
    lines = [f"date_utc: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
             f"commit: {sh('git rev-parse HEAD')}",
             "--- nproc", sh("nproc"), "--- free -g", sh("free -g"),
             "--- lscpu", sh("lscpu | grep -E 'Model name|^CPU\\(s\\)'"),
             f"--- ollama version: {version}", f"--- ollama tags: {tags}"]
    (out / "env.txt").write_text("\n".join(lines) + "\n")


def expand(text):
    """Cells may use $NAME for values chosen after earlier measurements."""
    out = os.path.expandvars(text)
    if "$" in out:
        raise SystemExit(f"unset variable in {text!r}")
    return out


def pipeline_command(cell, args, rep_dir, b_dll):
    base = ["--pdf", args.pdf, "--model", expand(cell["model"]), "--ollama", args.ollama, "--questions", args.questions, "--out", str(rep_dir),
            "--conversation", cell.get("conversation", "fresh")]
    for item in cell.get("set", []):
        base += ["--set", expand(item)]
    if cell["impl"] == "a":
        return [sys.executable, str(ROOT / "pipelines/a_python/rag_a.py"), *base]
    return ["dotnet", str(b_dll), *base]


def build_b(out):
    dll_dir = out / "_build_b"
    subprocess.run(["dotnet", "build", str(ROOT / "pipelines/b_dotnet"), "-c", "Release", "-o", str(dll_dir), "-v", "q"],
                   check=True, capture_output=True)
    return dll_dir / "PipelineB.dll"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ollama", default="http://localhost:11434")
    ap.add_argument("--questions", default="questions/questions.csv")
    ap.add_argument("--cell", action="append", help="run only this cell; repeatable")
    ap.add_argument("--rep", action="append", type=int, help="run only this repeat number; repeatable")
    args = ap.parse_args(argv)

    exp = json.load(open(args.experiment))
    if args.cell:
        exp["cells"] = [c for c in exp["cells"] if c["id"] in args.cell]
        if not exp["cells"]:
            raise SystemExit(f"no cell named {args.cell}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write_env(out, args.ollama)
    b_dll = build_b(out) if any(c["impl"] == "b" for c in exp["cells"]) else None

    rows = []
    for cell in exp["cells"]:
        for rep in args.rep or range(1, exp.get("repeats", 3) + 1):
            rep_dir = out / cell["id"] / f"rep-{rep}"
            rep_dir.mkdir(parents=True, exist_ok=True)
            code, wall, pipe_kb, ollama_kb = run_sampled(pipeline_command(cell, args, rep_dir, b_dll), cwd=ROOT,
                                                         stdout=open(rep_dir / "stdout.txt", "w"), stderr=subprocess.STDOUT)
            run = json.load(open(rep_dir / "run.json")) if (rep_dir / "run.json").exists() else {}
            answers = [json.loads(l) for l in open(rep_dir / "answers.jsonl")] if (rep_dir / "answers.jsonl").exists() else []
            rows.append({"experiment": exp["id"], "cell": cell["id"], "rep": rep, "exit_code": code, "wall_s": round(wall, 3),
                         "pipeline_peak_rss_kb": pipe_kb, "ollama_peak_rss_kb": ollama_kb,
                         "index_build_s": run.get("index_build_s"), "index_bytes": run.get("index_bytes"),
                         "index_bytes_basis": run.get("index_bytes_basis"), "answers": len(answers),
                         "mean_answer_s": round(sum(a["wall_s"] for a in answers) / len(answers), 3) if answers else None})
    with open(out / "resources.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else [])
        w.writeheader()
        w.writerows(rows)
    return 0 if all(r["exit_code"] == 0 for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
