#!/usr/bin/env python3
"""Count how many prompt tokens a model is offered and how many it uses under its default context window.

usage: check_prompt_truncation.py <pages-dir> <out-dir> <model>
Tokens used: the prompt_eval_count of the prompt sent with the default window, num_predict 1.
Tokens offered: the prompt is cut into pieces of about 3000 characters at word boundaries. Each piece is sent alone with
num_ctx raised, and the offered count is the sum of the piece counts minus the template overhead of every piece after the
first. Ollama limits num_ctx to the context length the model was trained with, so a single raised pass cannot count a
prompt longer than that. The single raised pass is kept as a cross-check for prompts that fit. The window in effect is
read from /api/ps after each pass. Prompts are built the way the pipelines build them, from whole pages (B) or three
1000-character chunks (A).
"""
import csv, functools, glob, json, os, re, sys, time, urllib.request

BASE = os.environ.get("OLLAMA_URL", "http://localhost:11434")

PAGES = [1, 2, 3, 5, 8]
RAISED = 32768
QUESTION = "What must be checked before the boiler is started for the first time?"


def call(path, body):
    req = urllib.request.Request(BASE + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=7200))


def window(model):
    """The window /api/ps reports. Older Ollama releases do not report it. WINDOW_ASSUMED then names the default window of that release."""
    ps = json.load(urllib.request.urlopen(BASE + "/api/ps", timeout=60))
    for m in ps.get("models", []):
        if m["name"].split(":")[0] == model.split(":")[0] and m.get("context_length"):
            return m["context_length"]
    return int(os.environ["WINDOW_ASSUMED"]) if os.environ.get("WINDOW_ASSUMED") else None


def text_rich_pages(pages_dir):
    pages = [re.sub(r"\s+", " ", open(p).read()).strip() for p in sorted(glob.glob(f"{pages_dir}/*.txt"))]
    start = int(len(pages) * 0.25)
    return [p for p in pages[start:] if len(p) > 2500]


def prompts(pages_dir, cfg):
    rich = text_rich_pages(pages_dir)
    out = []
    a_ctx = "\n".join(p[:1000] for p in rich[:3])
    out.append(("A", 3, [{"role": "system", "content": cfg["a"]["grounding"]["system"]},
                         {"role": "user", "content": QUESTION + "\n\nRelevant Context:\n" + a_ctx}]))
    b = cfg["b"]["grounding"]
    for n in PAGES:
        text = b["template"].replace("{shortest_line}", b["shortest_line"]).replace("{context}", "\n\n".join(rich[:n])).replace("{question}", QUESTION)
        out.append(("B", n, [{"role": "user", "content": text}]))
    return out


def count(model, messages, num_ctx=None):
    options = {"temperature": 0, "seed": 42, "num_predict": 1}
    if num_ctx:
        options["num_ctx"] = num_ctx
    t0 = time.time()
    r = call("/api/chat", {"model": model, "messages": messages, "stream": False, "options": options})
    return r["prompt_eval_count"], window(model), time.time() - t0


def split_pieces(text, size=3000):
    pieces, cur, n = [], [], 0
    for word in text.split(" "):
        if cur and n + len(word) + 1 > size:
            pieces.append(" ".join(cur))
            cur, n = [], 0
        cur.append(word)
        n += len(word) + 1
    if cur:
        pieces.append(" ".join(cur))
    return pieces


def template_overhead(model):
    """Tokens that the chat template adds around one user message."""
    one = count(model, [{"role": "user", "content": "a"}], RAISED)[0]
    two = count(model, [{"role": "user", "content": "a a"}], RAISED)[0]
    return one - (two - one)


@functools.lru_cache(maxsize=None)
def piece_count(model, text):
    return count(model, [{"role": "user", "content": text}], RAISED)[0]


def offered_by_pieces(model, messages, overhead):
    pieces = [p for m in messages for p in split_pieces(m["content"])]
    counts = [piece_count(model, p) for p in pieces]
    return sum(counts) - overhead * (len(pieces) - 1), len(pieces)


def main(pages_dir, out_dir, model, cfg_path="config/pipelines.json"):
    os.makedirs(out_dir, exist_ok=True)
    cfg = json.load(open(cfg_path))
    work = prompts(pages_dir, cfg)
    used = {}
    for shape, n, messages in work:
        used[(shape, n)] = count(model, messages)
    rows = []
    overhead = template_overhead(model)
    for shape, n, messages in work:
        single, raised_window, raised_s = count(model, messages, RAISED)
        offered, pieces = offered_by_pieces(model, messages, overhead)
        u, default_window, default_s = used[(shape, n)]
        rows.append({"model": model, "shape": shape, "units": n, "prompt_chars": sum(len(m["content"]) for m in messages),
                     "window_default": default_window, "window_raised": raised_window,
                     "tokens_offered": offered, "offered_pieces": pieces, "template_overhead": overhead,
                     "tokens_single_raised_pass": single, "tokens_used": u, "tokens_dropped": offered - u if offered > default_window else 0,
                     "truncated": offered > default_window, "default_pass_s": round(default_s, 2), "raised_pass_s": round(raised_s, 2)})
        print(json.dumps(rows[-1]), flush=True)
    path = f"{out_dir}/prompt_truncation_{model.replace(':', '_')}.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    main(*sys.argv[1:4])
