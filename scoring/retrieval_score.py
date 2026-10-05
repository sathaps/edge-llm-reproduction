import csv, json
from collections import OrderedDict

from questions import parse_pages, verified


def score_run(questions, retrieval_rows, config_id):
    """One row per verified question: were the reference pages, and for applicability the exclusion pages, retrieved?"""
    by_q = {r["question_id"]: r for r in retrieval_rows}
    out = []
    for q in verified(questions):
        ret = by_q.get(q["id"], {"retrieved": []})
        src, exc = parse_pages(q["source_pages"]), parse_pages(q["exclusion_pages"])
        got = [set(h["pages"]) for h in ret["retrieved"]]
        union = set().union(*got) if got else set()
        first = next((i + 1 for i, p in enumerate(got) if p & src), None) if src else None
        row = {"config_id": config_id, "question_id": q["id"], "category": q["category"],
               "reference_pages": sorted(src), "retrieved_pages": sorted(union),
               "n_retrieved": len(got),
               "any_reference_page": bool(src & union) if src else None,
               "all_reference_pages": src <= union if src else None,
               "first_hit_rank": first,
               "exclusion_retrieved": bool(exc & union) if q["category"] == "applicability" else None}
        out.append(row)
    return out


def summarise(rows):
    """Counts as n of N per category. Unanswerable questions have no reference page and are reported as returning something."""
    cats = OrderedDict()
    for r in rows:
        c = cats.setdefault(r["category"], {"N": 0, "any": 0, "all": 0, "exclusion_N": 0, "exclusion": 0, "returned_nothing": 0})
        c["N"] += 1
        if r["any_reference_page"] is not None:
            c["any"] += bool(r["any_reference_page"])
            c["all"] += bool(r["all_reference_pages"])
        else:
            c["returned_nothing"] += r["n_retrieved"] == 0
        if r["exclusion_retrieved"] is not None:
            c["exclusion_N"] += 1
            c["exclusion"] += bool(r["exclusion_retrieved"])
    return cats


def write_csv(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else [])
        w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v) if isinstance(v, list) else v for k, v in r.items()})
