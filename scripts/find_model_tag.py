#!/usr/bin/env python3
"""List the tags of an Ollama library model with the id that `ollama list` would show, and mark the ones that match.

usage: find_model_tag.py <model> <wanted-id> <out.csv>
The id of a tag is the first 12 characters of the SHA-256 of its manifest. The listing is checked against the tags
whose ids are already known from a pull, which are given as TAG=ID arguments after the output path.
"""
import csv, hashlib, json, os, re, sys, urllib.error, urllib.request

REGISTRY = os.environ.get("OLLAMA_REGISTRY", "https://registry.ollama.ai/v2/library")
ACCEPT = "application/vnd.docker.distribution.manifest.v2+json"


def get(url, accept=None):
    req = urllib.request.Request(url, headers={"Accept": accept} if accept else {})
    return urllib.request.urlopen(req, timeout=60).read()


def tags(model):
    try:
        return json.loads(get(f"{REGISTRY}/{model}/tags/list"))["tags"]
    except (urllib.error.URLError, KeyError, ValueError):
        page = get(f"https://ollama.com/library/{model}/tags").decode()
        return sorted(set(re.findall(rf"/library/{model}:([A-Za-z0-9._-]+)", page)))


def tag_id(model, tag):
    body = get(f"{REGISTRY}/{model}/manifests/{tag}", ACCEPT)
    return hashlib.sha256(body).hexdigest()[:12]


def main(model, wanted, out, known):
    rows = []
    for t in tags(model):
        try:
            rows.append({"tag": t, "id": tag_id(model, t)})
        except urllib.error.URLError as e:
            rows.append({"tag": t, "id": f"error: {e}"})
    for r in rows:
        r["matches_wanted"] = r["id"] == wanted
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tag", "id", "matches_wanted"])
        w.writeheader()
        w.writerows(rows)
    by = {r["tag"]: r["id"] for r in rows}
    for item in known:
        tag, _, want = item.partition("=")
        print(f"self-check {tag}: registry {by.get(tag)} expected {want} -> {'ok' if by.get(tag) == want else 'MISMATCH'}")
    hits = [r["tag"] for r in rows if r["matches_wanted"]]
    print(f"{len(rows)} tags listed; tags with id {wanted}: {hits or 'none'}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
