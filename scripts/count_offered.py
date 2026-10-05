#!/usr/bin/env python3
"""Add the exact count of offered prompt tokens to the answers of one run, then remove the prompts file.

usage: count_offered.py <run-dir> [--ollama URL]
Reads prompts.jsonl and answers.jsonl. A prompt that the default window cut keeps about half the window, so an answer
whose prompt_eval_count is below 40 percent of the window cannot have been cut and is not counted again. The others
are counted as in check_prompt_truncation.py. Adds tokens_offered, tokens_dropped and prompt_truncated to each answer.
"""
import argparse, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_prompt_truncation as cp

NOT_CUT_BELOW = 0.4


def annotate(run_dir, ollama):
    saved, cp.BASE = cp.BASE, ollama
    try:
        return _annotate(run_dir)
    finally:
        cp.BASE = saved


def _annotate(run_dir):
    run_dir = Path(run_dir)
    answers = [json.loads(l) for l in open(run_dir / "answers.jsonl")]
    prompts = {r["question_id"]: r["messages"] for r in map(json.loads, open(run_dir / "prompts.jsonl"))}
    model = json.load(open(run_dir / "run.json"))["model"]
    overhead = None
    for a in answers:
        used, ctx = a["prompt_eval_count"], a["context_length"]
        if ctx is None or used is None or used < NOT_CUT_BELOW * ctx:
            offered = used
        else:
            overhead = cp.template_overhead(model) if overhead is None else overhead
            offered = cp.offered_by_pieces(model, prompts[a["question_id"]], overhead)[0]
        cut = bool(ctx and offered is not None and offered > ctx)
        a.update(tokens_offered=offered, tokens_dropped=offered - used if cut else 0, prompt_truncated=cut)
    with open(run_dir / "answers.jsonl", "w") as f:
        f.writelines(json.dumps(a) + "\n" for a in answers)
    os.remove(run_dir / "prompts.jsonl")
    return answers


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--ollama", default="http://localhost:11434")
    a = ap.parse_args()
    rows = annotate(a.run_dir, a.ollama)
    print(f"{len(rows)} answers, {sum(r['prompt_truncated'] for r in rows)} with a cut prompt")
