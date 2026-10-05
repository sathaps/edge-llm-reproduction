"""Markdown tables of counts as n of N, one cell per configuration and category.

A configuration label is `<cell>@<rep>`, for example `A-llama3@2`. The repeats of one cell are shown in one table cell,
separated by " / ", and a cell whose repeats differ is marked with an asterisk.
"""
from collections import OrderedDict, defaultdict

from questions import MINIMUM

CATEGORIES = list(MINIMUM)


def split_label(label):
    cell, _, rep = label.partition("@")
    return cell, rep or "1"


def collect(rows, category_key, is_hit):
    """rows -> {cell: {category: {rep: (hits, total)}}}"""
    out = OrderedDict()
    for r in rows:
        hit = is_hit(r)
        if hit is None:
            continue
        cell, rep = split_label(r["config_id"])
        h, n = out.setdefault(cell, defaultdict(dict))[r[category_key]].get(rep, (0, 0))
        out[cell][r[category_key]][rep] = (h + bool(hit), n + 1)
    return out


def render(collected):
    head = "| Configuration | " + " | ".join(CATEGORIES) + " |\n|---|" + "---|" * len(CATEGORIES) + "\n"
    lines = []
    for cell, cats in collected.items():
        cols = []
        for cat in CATEGORIES:
            reps = cats.get(cat, {})
            if not reps:
                cols.append("n/a")
                continue
            ordered = [reps[k] for k in sorted(reps)]
            text = " / ".join(f"{h} of {n}" for h, n in ordered)
            cols.append(text + ("*" if len(set(ordered)) > 1 else ""))
        lines.append(f"| {cell} | " + " | ".join(cols) + " |")
    return head + "\n".join(lines) + "\n"


def retrieval_table(score_rows):
    """Reference page retrieved, n of N. Unanswerable questions have no reference page and show n/a."""
    return render(collect(score_rows, "category", lambda r: r["any_reference_page"]))


def exclusion_table(score_rows):
    """Applicability questions only: was the chunk with the exclusion retrieved."""
    return render(collect(score_rows, "category", lambda r: r["exclusion_retrieved"]))


def correct_table(marked):
    """Answers marked correct, n of N."""
    return render(collect(marked, "category", lambda r: r["correct"] == "yes"))
