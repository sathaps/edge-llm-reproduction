#!/usr/bin/env python3
"""Count garbled chunks and how often they are retrieved, for one pipeline run.

usage: garbled_chunks.py <run-dir>
A chunk is garbled when its text has control characters from unmapped glyph codes, or reads as English only after the constant shift is undone.
Reads chunks.jsonl and retrieval.jsonl and writes garbled.json with counts and page numbers only, never text.
"""
import json, re, sys
from pathlib import Path

COMMON = re.compile(r"\b(the|and|to|of|is|or|for|in|a|be|if|that|with|are|not)\b", re.I)
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f]")


def shifted(text):
    """Text of fonts without a Unicode map comes out shifted by 29 code points."""
    return "".join(chr(ord(c) + 29) if 3 <= ord(c) <= 94 else c for c in text)


def is_garbled(text):
    """Control characters from unmapped glyphs, or text that has few common words as it stands and many once shifted back."""
    body = text.strip()
    if len(body) < 200:
        return False
    if len(CONTROL.findall(body)) / len(body) > 0.02:
        return True
    raw, back = len(COMMON.findall(body)), len(COMMON.findall(shifted(body)))
    return back >= 5 and back > 3 * raw


def measure(run_dir):
    run_dir = Path(run_dir)
    chunks = [json.loads(l) for l in open(run_dir / "chunks.jsonl")]
    garbled = {c["chunk_id"] for c in chunks if is_garbled(c["text"])}
    pages = sorted({p for c in chunks if c["chunk_id"] in garbled for p in c["pages"]})
    out = {"chunks": len(chunks), "vectors": len(chunks), "garbled_chunks": len(garbled), "pages_with_a_garbled_chunk": pages}
    path = run_dir / "retrieval.jsonl"
    if path.exists():
        rows = [json.loads(l) for l in open(path)]
        slots = [h["chunk_id"] for r in rows for h in r["retrieved"]]
        out.update(questions=len(rows), retrieved_slots=len(slots), garbled_slots=sum(c in garbled for c in slots),
                   questions_with_a_garbled_chunk=sum(any(h["chunk_id"] in garbled for h in r["retrieved"]) for r in rows))
    json.dump(out, open(run_dir / "garbled.json", "w"), indent=1)
    return out


if __name__ == "__main__":
    print(json.dumps(measure(sys.argv[1])))
