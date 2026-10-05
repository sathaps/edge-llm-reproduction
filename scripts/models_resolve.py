#!/usr/bin/env python3
"""Check whether today's Ollama tags resolve to the ids seen on the original machine.

usage: models_resolve.py <out-dir>
Also measures the embedding dimension of both embedding models.
"""
import json, os, sys, urllib.request

out = sys.argv[1]; os.makedirs(out, exist_ok=True)
# 12-character ids from `ollama list` on the original machine
EXPECTED = {
    "llama3:latest": "365c0bd3c000",
    "mistral:latest": "f974a74358d6",
    "tinyllama:latest": "2644915ede35",
    "mxbai-embed-large:latest": "468836162de7",
    "all-minilm:latest": "1b226e2802db",
}
EXTRA = ["mistral:7b", "llama3.2:3b"]  # setup-probe tags, listed for comparison

def get(path):
    return json.load(urllib.request.urlopen("http://localhost:11434" + path, timeout=60))

def post(path, body):
    req = urllib.request.Request("http://localhost:11434" + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=300))

tags = {m["name"]: m for m in get("/api/tags")["models"]}
rows = ["tag,expected_id,actual_id,matches,size_bytes"]
for tag, exp in list(EXPECTED.items()) + [(t, "") for t in EXTRA]:
    m = tags.get(tag)
    act = m["digest"][:12] if m else "NOT_PULLED"
    rows.append(f"{tag},{exp},{act},{'yes' if exp and act == exp else ('n/a' if not exp else 'no')},{m['size'] if m else ''}")
open(f"{out}/models_resolve.csv", "w").write("\n".join(rows) + "\n")
print("\n".join(rows))
dims = {}
for tag in ("mxbai-embed-large:latest", "all-minilm:latest"):
    try:
        e = post("/api/embed", {"model": tag, "input": "test"})["embeddings"][0]
        dims[tag] = len(e)
    except Exception as ex:
        dims[tag] = f"error: {ex}"
json.dump(dims, open(f"{out}/embedding_dims.json", "w"), indent=1)
print("embedding dimensions:", dims)
