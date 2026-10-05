#!/usr/bin/env python3
"""E5: the whole manual text is placed in the system prompt and the model runs with its default context window.

usage: rag_e5.py --pdf MANUAL.pdf --model mistral:latest --questions questions/questions.csv --out results/<run-id>
The context window is not changed. The prompt token count and the context length in effect are recorded per answer
so that silent truncation is visible. prompts.jsonl holds the prompts for scripts/count_offered.py, which counts the
tokens offered and then removes the file.
"""
import argparse, csv, hashlib, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "a_python"))
import rag_a

SYSTEM = "Answer the user's questions using the following documentation.\n\n"


def run(args):
    ollama = rag_a.Ollama(args.ollama)
    os.makedirs(args.out, exist_ok=True)
    text, starts = rag_a.flatten_pages(args.pdf)
    system = SYSTEM + text
    cfg = {"temperature": 0, "seed": 42, "generation": {"max_tokens": None, "stop": None}}
    rows, prompts = [], []
    for q in rag_a.read_questions(args):
        messages = [{"role": "system", "content": system}, {"role": "user", "content": q["question"]}]
        reply = ollama.chat(args.model, messages, cfg)
        prompts.append({"question_id": q["id"], "messages": messages})
        ctx = ollama.context_length(args.model)
        pt = reply.get("prompt_eval_count")
        rows.append({"question_id": q["id"], "answer": reply["message"]["content"], "prompt_eval_count": pt,
                     "eval_count": reply.get("eval_count"), "context_length": ctx, "system_prompt_chars": len(system),
                     "done_reason": reply.get("done_reason")})
    rag_a.write_jsonl(f"{args.out}/answers.jsonl", rows)
    rag_a.write_jsonl(f"{args.out}/prompts.jsonl", prompts)
    json.dump({"experiment": "e5", "model": args.model, "model_digest": ollama.digest(args.model),
               "ollama_version": ollama.get("/api/version")["version"],
               "pdf_sha256": hashlib.sha256(open(args.pdf, "rb").read()).hexdigest(), "pages": len(starts),
               "manual_chars": len(text), "commit": rag_a.git_commit()}, open(f"{args.out}/run.json", "w"), indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--model", default="mistral:latest")
    ap.add_argument("--ollama", default="http://localhost:11434")
    ap.add_argument("--questions", default="questions/questions.csv")
    ap.add_argument("--question")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", required=True)
    run(ap.parse_args())
