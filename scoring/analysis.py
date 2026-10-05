"""Counts with Wilson intervals and exact McNemar tests on paired per-question outcomes.

Input rows have `config_id` (`<cell>@<rep>`), `question_id` and `outcome` (yes, partial or no). The primary outcome is
`yes`. The outcome with partial credit is `yes` or `partial`.
"""
import csv
import json
from math import comb, sqrt

Z = 1.959964


def wilson(k, n, z=Z):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(b, c):
    """Two-sided exact p-value for b and c discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def holm(pvalues):
    """Holm adjustment. pvalues: list of floats in any order. Returns the adjusted values in the same order."""
    order = sorted(range(len(pvalues)), key=lambda i: pvalues[i])
    adjusted, running = [None] * len(pvalues), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(pvalues) - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted


def split_label(label):
    cell, _, rep = label.partition("@")
    return cell, int(rep or 1)


def outcome_table(rows, partial_credit=False):
    """-> {(cell, rep): {question_id: 0 or 1}}"""
    good = {"yes", "partial"} if partial_credit else {"yes"}
    out = {}
    for r in rows:
        out.setdefault(split_label(r["config_id"]), {})[r["question_id"]] = int(r["outcome"].strip().lower() in good)
    return out


def counts(table):
    """-> list of dicts: cell, rep, correct, N, lo, hi"""
    out = []
    for (cell, rep), per_q in sorted(table.items()):
        k, n = sum(per_q.values()), len(per_q)
        lo, hi = wilson(k, n)
        out.append({"cell": cell, "rep": rep, "correct": k, "N": n, "wilson_lo": lo, "wilson_hi": hi})
    return out


def compare(table, a, b, rep):
    """Pair the questions that both cells have. Returns b_only is the count of questions right in a but not in b."""
    qa, qb = table.get((a, rep), {}), table.get((b, rep), {})
    shared = sorted(set(qa) & set(qb))
    right_a_only = sum(1 for q in shared if qa[q] and not qb[q])
    right_b_only = sum(1 for q in shared if qb[q] and not qa[q])
    return {"N_paired": len(shared), "a_correct": sum(qa[q] for q in shared), "b_correct": sum(qb[q] for q in shared),
            "a_only": right_a_only, "b_only": right_b_only, "p_exact": mcnemar_exact(right_a_only, right_b_only)}


def run_comparisons(rows, comparisons, partial_credit=False):
    table = outcome_table(rows, partial_credit)
    results = []
    for c in comparisons:
        results.append({"id": c["id"], "a": c["a"], "b": c["b"], "rep": c.get("rep", 1), **compare(table, c["a"], c["b"], c.get("rep", 1))})
    for r, adj in zip(results, holm([r["p_exact"] for r in results])):
        r["p_holm"] = adj
    return results


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def run(outcomes_csv, comparisons_json, out_prefix):
    rows = list(csv.DictReader(open(outcomes_csv, newline="")))
    comps = json.load(open(comparisons_json))["comparisons"]
    for name, partial in (("", False), ("_with_partial", True)):
        write_csv(f"{out_prefix}_counts{name}.csv", counts(outcome_table(rows, partial)))
        write_csv(f"{out_prefix}_comparisons{name}.csv", run_comparisons(rows, comps, partial))
