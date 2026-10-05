#!/usr/bin/env python3
"""Record what the legacy /api/embeddings endpoint and /api/embed do with inputs longer than the model's window.

usage: check_legacy_embed.py <out-csv> [model ...]
LangChain .NET 0.17.0 and the upstream Python script call /api/embeddings. Inputs are runs of 50 to 2000 short words.
For each endpoint and length the CSV has the HTTP status and, on success, the prompt token count the server reports.
"""
import csv, json, os, sys, urllib.error, urllib.request

import check_embedding_truncation as ce

LENGTHS = [50, 100, 150, 200, 250, 300, 400, 500, 600, 1000, 2000]


def post(path, body):
    req = urllib.request.Request(ce.BASE + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=600))
        return 200, r.get("prompt_eval_count"), ""
    except urllib.error.HTTPError as e:
        return e.code, None, json.loads(e.read() or "{}").get("error", "")


def main(out, models):
    rows = []
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    for model in models:
        post("/api/embed", {"model": model, "input": "warm up"})
        for n in LENGTHS:
            text = " ".join(f"w{i}" for i in range(n))
            for path, body in (("/api/embeddings", {"model": model, "prompt": text}), ("/api/embed", {"model": model, "input": text})):
                status, tokens, error = post(path, body)
                rows.append({"model": model, "endpoint": path, "words": n, "http_status": status, "prompt_eval_count": tokens, "error": error})
                print(json.dumps(rows[-1]), flush=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or ce.MODELS)
