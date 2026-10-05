#!/usr/bin/env python3
"""Time retrieval-sized prompts built from real manual pages.

usage: budget_probe.py <pages-dir> <out-dir> <model> [<model> ...]
A_like is three 1000-character chunks (A's retrieval depth), B_like is five whole
pages (B's). Each shape is sent twice per model after a warm-up. num_ctx stays at
the Ollama default; the context length in effect is read from /api/ps. num_predict
is capped at 256 to bound job time, and calls that reach the cap are flagged.
"""
import glob, json, os, sys, time, urllib.request

pages_dir, out = sys.argv[1], sys.argv[2]; models = sys.argv[3:]
os.makedirs(out, exist_ok=True)
H = "http://localhost:11434"

def post(path, body, timeout=1200):
    req = urllib.request.Request(H + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))

def get(path):
    return json.load(urllib.request.urlopen(H + path, timeout=60))

pages = [open(p).read() for p in sorted(glob.glob(f"{pages_dir}/*.txt"))]
n = len(pages)
usable = [i for i in range(int(n * 0.25), n) if len(pages[i].strip()) > 2500]
pick = usable[:5]
assert len(pick) == 5, f"need 5 text-rich pages, found {len(pick)}"
chunks = [pages[i].strip()[:1000] for i in pick[:3]]
whole = [pages[i].strip() for i in pick]
Q = "What must be done before starting the unit, and in what order?"
SHAPES = {
    "A_like": ("\n\n".join(chunks), 3),
    "B_like": ("\n\n".join(whole), 5),
}
rows = []
for model in models:
    post("/api/generate", {"model": model, "prompt": "Say OK.", "stream": False,
                           "options": {"temperature": 0, "seed": 42, "num_predict": 4}})
    for shape, (ctx, k) in SHAPES.items():
        prompt = f"Use this context from the manual to answer.\n\nContext:\n{ctx}\n\nQuestion: {Q}\nAnswer:"
        for rep in (1, 2):
            t0 = time.time()
            r = post("/api/generate", {"model": model, "prompt": prompt, "stream": False,
                                       "options": {"temperature": 0, "seed": 42, "num_predict": 256}})
            wall = time.time() - t0
            ps = get("/api/ps")
            m = next((x for x in ps.get("models", []) if x.get("name") == model), {})
            row = {"model": model, "shape": shape, "chunks": k, "rep": rep, "pages_used": [i + 1 for i in pick[:k]],
                   "prompt_chars": len(prompt), "wall_s": round(wall, 3),
                   "prompt_eval_count": r.get("prompt_eval_count"), "prompt_eval_ns": r.get("prompt_eval_duration"),
                   "eval_count": r.get("eval_count"), "eval_ns": r.get("eval_duration"),
                   "load_ns": r.get("load_duration"), "total_ns": r.get("total_duration"),
                   "done_reason": r.get("done_reason"), "capped_at_num_predict": r.get("eval_count") == 256,
                   "ps_context_length": m.get("context_length"), "ps_size_vram": m.get("size_vram"),
                   "ps_size": m.get("size"), "response": r.get("response")}
            rows.append(row)
            print(json.dumps({k2: v for k2, v in row.items() if k2 != "response"}), flush=True)
    show = {}
    try:
        show = post("/api/show", {"model": model})
    except Exception as e:
        show = {"error": str(e)}
    json.dump({"parameters": show.get("parameters"), "details": show.get("details"),
               "model_info_context_length": {k: v for k, v in (show.get("model_info") or {}).items() if "context_length" in k}},
              open(f"{out}/show_{model.replace(':','_')}.json", "w"), indent=1)
json.dump(rows, open(f"{out}/budget_calls.json", "w"), indent=1)
