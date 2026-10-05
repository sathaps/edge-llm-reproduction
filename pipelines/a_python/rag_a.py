#!/usr/bin/env python3
"""Implementation A: single-file local retrieval over Ollama, after easy-local-rag.

usage: rag_a.py --pdf MANUAL.pdf --model llama3:latest --questions questions/questions.csv --out results/<run-id>
Settings come from config/pipelines.json (section "a"); --set path=value overrides one key.
"""
import argparse, bisect, csv, hashlib, json, os, re, subprocess, sys, time, urllib.request

import numpy as np
from pypdf import PdfReader


def load_config(path, section, overrides=()):
    cfg = json.load(open(path))
    merged = {**cfg["common"], **cfg[section]}
    for item in overrides:
        key, _, raw = item.partition("=")
        node = merged
        *parents, leaf = key.split(".")
        for p in parents:
            node = node[p]
        node[leaf] = json.loads(raw)
    return merged


class Ollama:
    def __init__(self, url):
        self.url = url.rstrip("/")

    def get(self, path):
        return json.load(urllib.request.urlopen(self.url + path, timeout=60))

    def post(self, path, body):
        req = urllib.request.Request(self.url + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=3600))

    def embed(self, model, texts, batch=16):
        out = []
        for i in range(0, len(texts), batch):
            out += self.post("/api/embed", {"model": model, "input": texts[i:i + batch]})["embeddings"]
        return np.array(out, dtype=np.float32)

    def chat(self, model, messages, cfg):
        options = {"temperature": cfg["temperature"], "seed": cfg["seed"]}
        gen = cfg["generation"]
        if gen.get("max_tokens"):
            options["num_predict"] = gen["max_tokens"]
        if gen.get("stop"):
            options["stop"] = gen["stop"]
        if gen.get("num_ctx"):
            options["num_ctx"] = gen["num_ctx"]
        return self.post("/api/chat", {"model": model, "messages": messages, "stream": False, "options": options})

    def context_length(self, model):
        for m in self.get("/api/ps").get("models", []):
            if m["name"] == model or m["name"].split(":")[0] == model.split(":")[0]:
                return m.get("context_length")
        return None

    def digest(self, model):
        for m in self.get("/api/tags")["models"]:
            if m["name"] == model or (":" not in model and m["name"] == model + ":latest"):
                return m["digest"]
        return None


def flatten_pages(pdf_path):
    """Whitespace-flattened text of the whole document, plus the offset where each page starts."""
    pages = [re.sub(r"\s+", " ", (p.extract_text() or "")).strip() for p in PdfReader(pdf_path).pages]
    starts, text = [], ""
    for page in pages:
        starts.append(len(text))
        text += page + " "
    return text.strip(), starts


def sentence_spans(text):
    spans, start = [], 0
    for m in re.finditer(r"(?<=[.!?]) +", text):
        spans.append((start, m.start()))
        start = m.end()
    spans.append((start, len(text)))
    return [s for s in spans if s[1] > s[0]]


def chunk_text(text, starts, max_chars):
    """Group sentences as upload.py of the upstream project does.

    Upstream adds each sentence with `(sentence + " ").strip()`, so sentences inside a chunk run together without a
    space. Only the first sentence after a cut keeps its trailing space. We keep that behaviour, because the defaults
    are what is measured. A sentence of max_chars or more is cut off as a chunk of its own.
    """
    chunks, cur, first, last = [], "", None, None

    def close():
        if cur.strip():
            chunks.append((cur.strip(), first, last))

    for s, e in sentence_spans(text):
        sentence = text[s:e]
        if len(cur) + len(sentence) + 1 < max_chars:
            cur += (sentence + " ").strip()
            first = s if first is None else first
            last = e
        else:
            close()
            cur, first, last = sentence + " ", s, e
    close()
    out = []
    for i, (body, s, e) in enumerate(chunks):
        a = bisect.bisect_right(starts, s) - 1
        b = bisect.bisect_right(starts, max(s, e - 1)) - 1
        out.append({"chunk_id": f"c{i:04d}", "pages": list(range(a + 1, b + 2)), "text": body})
    return out


def retrieve(query_vec, matrix, top_k, min_score):
    scores = matrix @ query_vec
    order = np.argsort(-scores)[:top_k]
    return [(int(i), float(scores[i])) for i in order if min_score is None or scores[i] >= min_score]


def normalise(m):
    m = np.atleast_2d(m)
    return m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-12)


def rewrite_query(ollama, model, cfg, question, history):
    """Upstream builds the history text from the last messages after the current question has been appended."""
    rw = cfg["query_rewriting"]
    recent = (history + [{"role": "user", "content": question}])[-rw["history_messages"]:]
    hist = "\n".join(f"{m['role']}: {m['content']}" for m in recent)
    prompt = rw["template"].replace("{history}", hist).replace("{question}", question)
    reply = ollama.chat(model, [{"role": rw.get("role", "user"), "content": prompt}], {**cfg, "generation": {"max_tokens": 200}})
    return reply["message"]["content"].strip()


def run(args):
    cfg = load_config(args.config, "a", args.set)
    ollama = Ollama(args.ollama)
    os.makedirs(args.out, exist_ok=True)

    text, starts = flatten_pages(args.pdf)
    chunks = chunk_text(text, starts, cfg["chunking"]["max_chars"])
    t0 = time.time()
    # upstream embeds the lines of vault.txt, which end with a newline
    matrix = normalise(ollama.embed(cfg["embedding_model"], [c["text"] + "\n" for c in chunks]))
    index_s = time.time() - t0
    with open(f"{args.out}/chunks.jsonl", "w") as f:
        for c in chunks:
            f.write(json.dumps(c) + "\n")
    index_bytes = os.path.getsize(f"{args.out}/chunks.jsonl")  # the embeddings stay in memory, as in the original

    questions = read_questions(args)
    history, ret_rows, ans_rows, prompt_rows = [], [], [], []
    for q in questions:
        if args.conversation == "fresh":
            history = []
        turn = sum(1 for m in history if m["role"] == "user") + 1
        query = q["question"]
        rw = cfg.get("query_rewriting")
        if rw and turn >= rw["from_turn"] and not args.retrieval_only:
            query = rewrite_query(ollama, args.model, cfg, q["question"], history)
        qvec = normalise(ollama.embed(cfg["embedding_model"], [query]))[0]
        hits = retrieve(qvec, matrix, cfg["retrieval"]["top_k"], cfg["retrieval"]["min_score"])
        ret_rows.append({"question_id": q["id"], "query_used": query,
                         "retrieved": [{"chunk_id": chunks[i]["chunk_id"], "pages": chunks[i]["pages"], "score": s} for i, s in hits]})
        if args.retrieval_only:
            continue
        context = "\n".join(chunks[i]["text"] for i, _ in hits)
        user = q["question"] + "\n\nRelevant Context:\n" + context
        history.append({"role": "user", "content": user})
        messages = [{"role": "system", "content": cfg["grounding"]["system"]}] + history
        t1 = time.time()
        reply = ollama.chat(args.model, messages, cfg)
        prompt_rows.append({"question_id": q["id"], "messages": messages})
        wall = time.time() - t1
        answer = reply["message"]["content"]
        history.append({"role": "assistant", "content": answer})
        ctx = ollama.context_length(args.model)
        ans_rows.append({"question_id": q["id"], "answer": answer, "wall_s": wall,
                         "prompt_eval_count": reply.get("prompt_eval_count"), "prompt_eval_ns": reply.get("prompt_eval_duration"),
                         "eval_count": reply.get("eval_count"), "eval_ns": reply.get("eval_duration"),
                         "done_reason": reply.get("done_reason"), "context_length": ctx})

    write_jsonl(f"{args.out}/retrieval.jsonl", ret_rows)
    if not args.retrieval_only:
        write_jsonl(f"{args.out}/answers.jsonl", ans_rows)
        write_jsonl(f"{args.out}/prompts.jsonl", prompt_rows)
    json.dump({"implementation": "a", "settings": cfg, "model": args.model,
               "model_digest": None if args.retrieval_only else ollama.digest(args.model),
               "embedding_digest": ollama.digest(cfg["embedding_model"]),
               "ollama_version": ollama.get("/api/version")["version"],
               "pdf_sha256": hashlib.sha256(open(args.pdf, "rb").read()).hexdigest(),
               "pages": len(starts), "chunks": len(chunks), "index_build_s": index_s,
               "index_bytes": index_bytes, "index_bytes_basis": "chunks.jsonl",
               "conversation": args.conversation, "commit": git_commit()},
              open(f"{args.out}/run.json", "w"), indent=1)


def read_questions(args):
    if args.question:
        return [{"id": "q", "question": args.question}]
    rows = list(csv.DictReader(open(args.questions)))
    return rows[:args.limit] if args.limit else rows


def write_jsonl(path, rows):
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def git_commit():
    r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() or None


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--model", default="llama3:latest")
    ap.add_argument("--ollama", default="http://localhost:11434")
    ap.add_argument("--questions", default="questions/questions.csv")
    ap.add_argument("--question")
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", default="config/pipelines.json")
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--conversation", choices=["fresh", "chained"], default="fresh")
    ap.add_argument("--retrieval-only", action="store_true")
    ap.add_argument("--limit", type=int)
    return ap.parse_args(argv)


if __name__ == "__main__":
    run(parse_args())
