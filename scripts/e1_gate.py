#!/usr/bin/env python3
"""Sanity gate for a collected experiment: every cell is complete and nothing in it is an error recorded as an answer.

usage: e1_gate.py <results-dir> <rep> [--questions CSV] [--cells A-llama3,B-llama3,...] [--mode retrieve|none|oracle]
For every <results-dir>/<cell>/rep-<rep>/ it checks: one answer per question, in the order of the question file; an answer
is text; no answer looks like an error, a timeout or an HTTP error recorded as text; wall_s, prompt_eval_count,
tokens_offered, tokens_dropped, prompt_truncated and context_length are present for every question; retrieval rows exist for
every question; run.json names the commit, the Ollama version and the model digest. Prints a markdown table, then one line per
failure. Exit status 1 when any cell fails. It reads no marks and judges no answer for accuracy.
"""
import csv, json, re, sys
from pathlib import Path

ERROR = re.compile(r"^\s*(error|exception|traceback|http\s*\d{3}|\d{3}\s+(internal|bad|not found)|timeout|timed out|connection (refused|reset|error))|"
                   r"System\.\w+Exception|HttpRequestException|ConnectionError|ReadTimeout|Traceback \(most recent|status code \d{3}|"
                   r"\"error\"\s*:", re.I)
PER_ANSWER = ["answer", "wall_s", "prompt_eval_count", "eval_count", "context_length", "tokens_offered", "tokens_dropped", "prompt_truncated"]


def lines(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def gate_cell(d, qids, mode="retrieve"):
    fails = []
    answers = lines(d / "answers.jsonl") if (d / "answers.jsonl").exists() else None
    if answers is None:
        return {"answers": 0, "empty": 0, "cut": 0}, ["answers.jsonl is missing"]
    if [a.get("question_id") for a in answers] != qids:
        fails.append(f"answers are {len(answers)} rows; expected {len(qids)} in the order of the question file")
    empty = cut = 0
    for a in answers:
        q = a.get("question_id")
        for k in PER_ANSWER:
            if k not in a or (a[k] is None and k != "context_length"):
                fails.append(f"{q}: {k} is missing")
        if k := a.get("answer"):
            if not isinstance(k, str):
                fails.append(f"{q}: answer is not text")
            elif ERROR.search(k):
                fails.append(f"{q}: answer looks like an error: {k[:60]!r}")
        else:
            empty += 1
        if isinstance(a.get("prompt_eval_count"), int) and a["prompt_eval_count"] <= 0:
            fails.append(f"{q}: prompt_eval_count is {a['prompt_eval_count']}")
        cut += bool(a.get("prompt_truncated"))
    ret = lines(d / "retrieval.jsonl") if (d / "retrieval.jsonl").exists() else []
    if [r.get("question_id") for r in ret] != qids:
        fails.append(f"retrieval rows are {len(ret)}; expected {len(qids)}")
    elif mode == "retrieve":
        for r in ret:
            if "retrieved" not in r:
                fails.append(f"{r['question_id']}: retrieval row has no retrieved list")
    if not (d / "run.json").exists():
        fails.append("run.json is missing")
    else:
        run = json.load(open(d / "run.json"))
        for k in ("commit", "ollama_version", "model_digest"):
            if not run.get(k):
                fails.append(f"run.json has no {k}")
    if not (d / "garbled.json").exists():
        fails.append("garbled.json is missing")
    return {"answers": len(answers), "empty": empty, "cut": cut}, fails


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    opts = dict(zip(argv, argv[1:]))
    root, rep = Path(args[0]), args[1]
    qids = [r["id"] for r in csv.DictReader(open(opts.get("--questions", "questions/questions.csv")))]
    cells = opts["--cells"].split(",") if "--cells" in opts else sorted(p.name for p in root.iterdir() if p.is_dir() and (p / f"rep-{rep}").exists())
    bad, rows = 0, []
    for cell in cells:
        d = root / cell / f"rep-{rep}"
        if not d.exists():
            rows.append(f"| {cell} | missing | | | FAIL |")
            print(f"FAIL {cell}: {d} does not exist")
            bad += 1
            continue
        stats, fails = gate_cell(d, qids, opts.get("--mode", "retrieve"))
        rows.append(f"| {cell} | {stats['answers']} | {stats['empty']} | {stats['cut']} | {'FAIL' if fails else 'pass'} |")
        for f in fails:
            print(f"FAIL {cell}: {f}")
        bad += bool(fails)
    print("\n| Cell | Answers | Empty answers | Questions with a cut prompt | Gate |\n|---|---|---|---|---|\n" + "\n".join(rows))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
