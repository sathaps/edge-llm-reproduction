#!/usr/bin/env python3
"""Write one contiguous slice of a question file.

usage: make_shard.py <questions.csv> <shard 1..N> <N> <out.csv>
A job on a hosted runner stops after 6 hours, and one llama3 cell of B needs more. The questions of a cell are answered
one after the other and each in a fresh conversation, so a cell can be cut into shards that run in separate jobs without
changing any answer. The slices are contiguous, so concatenating the shards in order gives the question file again.
"""
import csv, sys


def shard_rows(rows, k, n):
    return rows[(k - 1) * len(rows) // n: k * len(rows) // n]


if __name__ == "__main__":
    src, k, n, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    reader = csv.DictReader(open(src, newline=""))
    rows = list(reader)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=reader.fieldnames)
        w.writeheader()
        w.writerows(shard_rows(rows, k, n))
