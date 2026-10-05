#!/usr/bin/env python3
"""Check whether an embedding model silently drops text beyond its context window.

usage: check_embedding_truncation.py <pages-dir> <out-dir> [model ...]
For each sampled page the script embeds the whole page with Ollama's default (truncating) behaviour, then embeds the
longest prefix that fits the window with truncate=false, and reports the cosine similarity of the two vectors. A
similarity of 1 means the rest of the page did not change the embedding. Tokens offered are the sum of the token counts
of consecutive pieces that each fit the window, so every count comes from Ollama.
"""
import csv, glob, json, math, os, re, statistics, sys, urllib.error, urllib.request

MODELS = ["all-minilm:latest", "mxbai-embed-large:latest"]
SAMPLE = 20
BASE = "http://localhost:11434"


def embed(model, text, truncate=True):
    body = json.dumps({"model": model, "input": text, "truncate": truncate}).encode()
    req = urllib.request.Request(BASE + "/api/embed", body, {"Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=600))
    except urllib.error.HTTPError:
        return None
    return r["embeddings"][0], r.get("prompt_eval_count")


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


ASSUMED = {"all-minilm": 256, "mxbai-embed-large": 512}


def window(model):
    """The window /api/ps reports. Older Ollama releases do not report it. ASSUME_WINDOWS=1 then uses the trained lengths."""
    ps = json.load(urllib.request.urlopen(BASE + "/api/ps", timeout=60))
    for m in ps.get("models", []):
        if m["name"] == model and m.get("context_length"):
            return m["context_length"]
    return ASSUMED.get(model.split(":")[0]) if os.environ.get("ASSUME_WINDOWS") else None


def longest_fitting_prefix(model, words, start=0):
    """Largest number of words from `start` whose text fits the window (truncate=false). Returns (count, vector, tokens)."""
    lo, hi, best = 1, len(words) - start, None
    while lo <= hi:
        mid = (lo + hi) // 2
        got = embed(model, " ".join(words[start:start + mid]), truncate=False)
        if got is None:
            hi = mid - 1
        else:
            best, lo = (mid, *got), mid + 1
    return best


def special_tokens(model):
    one, two = embed(model, "boiler")[1], embed(model, "boiler boiler")[1]
    if one is None or two is None:  # releases before 0.4 do not report prompt_eval_count on /api/embed
        return None
    return one - (two - one)


def med(values):
    values = list(values)
    return statistics.median(values) if values else None


def check_page(model, text, specials):
    words = text.split()
    full, used = embed(model, text)
    first = longest_fitting_prefix(model, words)
    n_prefix, prefix_vec, prefix_tokens = first
    offered, pos, tail_vec = prefix_tokens, n_prefix, None
    while pos < len(words):
        piece = longest_fitting_prefix(model, words, pos)
        if tail_vec is None:
            tail_vec = piece[1]
        offered = None if offered is None or piece[2] is None else offered + piece[2] - specials
        pos += piece[0]
    return {"chars": len(text), "tokens_offered": offered, "tokens_used": used, "prefix_words": n_prefix, "words": len(words),
            "cos_full_vs_prefix": cosine(full, prefix_vec), "cos_full_vs_tail": cosine(full, tail_vec) if tail_vec else None}


def sample_pages(pages_dir):
    pages = [re.sub(r"\s+", " ", open(p).read()).strip() for p in sorted(glob.glob(f"{pages_dir}/*.txt"))]
    rich = [p for p in pages if len(p) > 1500]
    step = max(1, len(rich) // SAMPLE)
    return rich[::step][:SAMPLE]


def main(pages_dir, out_dir, models):
    os.makedirs(out_dir, exist_ok=True)
    pages = sample_pages(pages_dir)
    detail, summary = [], []
    for model in models:
        embed(model, "warm up")
        win, specials = window(model), special_tokens(model)
        rows = [check_page(model, p, specials) for p in pages]
        for i, r in enumerate(rows):
            detail.append({"model": model, "page_sample": i + 1, "window": win, **r})
        summary.append({"model": model, "window_in_effect": win, "special_tokens_per_input": specials, "pages_tested": len(rows),
                        "median_chars": med(r["chars"] for r in rows),
                        "median_tokens_offered": med(r["tokens_offered"] for r in rows if r["tokens_offered"] is not None),
                        "median_tokens_used": med(r["tokens_used"] for r in rows if r["tokens_used"] is not None),
                        "pages_cut": sum(1 for r in rows if r["tokens_offered"] is not None and win and r["tokens_offered"] > win),
                        "pages_whose_prefix_is_shorter_than_the_page": sum(1 for r in rows if r["prefix_words"] < r["words"]),
                        "median_cos_full_vs_prefix": round(med(r["cos_full_vs_prefix"] for r in rows), 6),
                        "min_cos_full_vs_prefix": round(min(r["cos_full_vs_prefix"] for r in rows), 6),
                        "median_cos_full_vs_tail": round(med(r["cos_full_vs_tail"] for r in rows if r["cos_full_vs_tail"] is not None), 6)})
        print(json.dumps(summary[-1]), flush=True)
    for name, data in (("embedding_truncation_pages.csv", detail), ("embedding_truncation.csv", summary)):
        with open(f"{out_dir}/{name}", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:] or MODELS)
