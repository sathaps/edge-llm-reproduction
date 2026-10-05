#!/usr/bin/env python3
"""Measure whether text beyond an embedding model's window can be found through its page vector.

usage: check_embedding_retrieval.py <pages-dir> <out-dir> [model ...]
Each page is embedded once, as B does (one vector per page, Euclidean distance). The vectors come from /api/embed, which
cuts an over-long input to the window. The legacy /api/embeddings endpoint that LangChain .NET calls refuses such input
with HTTP 500 under Ollama 0.35.1 (see check_legacy_embed.py), so it cannot be used for page vectors.
A page is cut into passages of three consecutive sentences. A passage is "inside" when it lies wholly within the longest
prefix of its page that fits the window, and "beyond" when it starts after that prefix. Each passage is queried with its
own first sentence. A query is a hit when its page is among the 5 nearest page vectors. Queries whose sentence also occurs
on another page are left out. Only pages longer than the window take part, so both groups come from the same pages.
Output: embedding_retrieval.csv (counts) and embedding_retrieval_queries.csv (page numbers and ranks, no text).
No page text is printed.
"""
import csv, glob, json, math, os, random, re, sys, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_embedding_truncation as ce

MODELS = ["all-minilm:latest", "mxbai-embed-large:latest"]
TOP_K = 5
PER_GROUP = 150
PASSAGE_SENTENCES = 3
MIN_QUERY_WORDS = 5


def embed_vector(model, text):
    return ce.embed(model, text)[0]


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def load_pages(pages_dir):
    out = []
    for path in sorted(glob.glob(f"{pages_dir}/*.txt")):
        text = re.sub(r"\s+", " ", open(path).read()).strip()
        if len(text) >= 20:  # pages with no text (drawings) have nothing to embed
            out.append((int(os.path.basename(path).split(".")[0]), text))
    return out


def passages(text):
    """Yield (first word index, last word index + 1, first sentence) for runs of consecutive sentences."""
    sentences = re.split(r"(?<=[.!?]) +", text)
    pos, spans = 0, []
    for s in sentences:
        n = len(s.split())
        spans.append((pos, pos + n, s))
        pos += n
    for i in range(0, len(spans) - PASSAGE_SENTENCES + 1, PASSAGE_SENTENCES):
        group = spans[i:i + PASSAGE_SENTENCES]
        yield group[0][0], group[-1][1], group[0][2]


def run(pages_dir, out_dir, models, seed=42):
    os.makedirs(out_dir, exist_ok=True)
    pages = load_pages(pages_dir)
    occurrences = {}
    for number, text in pages:
        for s in set(re.split(r"(?<=[.!?]) +", text)):
            occurrences.setdefault(s, set()).add(number)
    summary, detail = [], []
    for model in models:
        ce.embed(model, "warm up")
        window = ce.window(model)
        vectors = {number: embed_vector(model, text) for number, text in pages}
        pool = {"inside": [], "beyond": []}
        long_pages = 0
        for number, text in pages:
            words = text.split()
            if len(words) < 50:
                continue
            fit = ce.longest_fitting_prefix(model, words)
            if fit is None or fit[0] >= len(words):
                continue
            long_pages += 1
            for start, end, first in passages(text):
                if len(first.split()) < MIN_QUERY_WORDS or occurrences[first] != {number}:
                    continue
                group = "inside" if end <= fit[0] else "beyond" if start >= fit[0] else None
                if group:
                    pool[group].append((number, start, first))
        rng = random.Random(seed)
        for group, items in pool.items():
            available = len(items)
            for number, start, first in rng.sample(items, min(PER_GROUP, available)):
                q = embed_vector(model, first)
                order = sorted(vectors, key=lambda n: distance(q, vectors[n]))
                rank = order.index(number) + 1
                detail.append({"model": model, "group": group, "page": number, "start_word": start, "rank": rank, "hit_top_k": rank <= TOP_K})
            rows = [d for d in detail if d["model"] == model and d["group"] == group]
            summary.append({"model": model, "window": window, "group": group, "pages_longer_than_window": long_pages,
                            "passages_available": available, "queries": len(rows), "hit_top5": sum(d["hit_top_k"] for d in rows),
                            "hit_top1": sum(d["rank"] == 1 for d in rows)})
            print(json.dumps(summary[-1]), flush=True)
    for name, data in (("embedding_retrieval.csv", summary), ("embedding_retrieval_queries.csv", detail)):
        with open(f"{out_dir}/{name}", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    return summary


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3:] or MODELS)
