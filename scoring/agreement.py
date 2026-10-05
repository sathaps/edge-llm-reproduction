"""Agreement between the automatic rubric and a person's marks, as n of N per criterion."""
from collections import OrderedDict

CRITERIA = ["correct", "complete", "respects_applicability", "abstained", "unsupported_content"]


def agreement(pairs):
    """pairs: iterable of (auto_row, person_row), both dicts with the criteria as keys. Empty person marks are skipped."""
    out = OrderedDict()
    for c in CRITERIA:
        n = agree = binary_agree = 0
        for auto, person in pairs:
            p, a = (person.get(c) or "").strip().lower(), (auto.get(c) or "").strip().lower()
            if not p or not a:
                continue
            n += 1
            agree += p == a
            binary_agree += (p == "yes") == (a == "yes")
        out[c] = {"N": n, "agree": agree, "agree_yes_vs_not_yes": binary_agree}
    return out


def render(result):
    lines = ["| Criterion | Same mark | Same on yes versus not yes |", "|---|---|---|"]
    for c, r in result.items():
        lines.append(f"| {c} | {r['agree']} of {r['N']} | {r['agree_yes_vs_not_yes']} of {r['N']} |")
    return "\n".join(lines) + "\n"


def cohen_kappa(pairs):
    """pairs: iterable of (label_1, label_2). Returns (kappa, N, agree). Kappa is None when chance agreement is 1."""
    pairs = [(a.strip().lower(), b.strip().lower()) for a, b in pairs if (a or "").strip() and (b or "").strip()]
    n = len(pairs)
    if n == 0:
        return None, 0, 0
    agree = sum(a == b for a, b in pairs)
    labels = {x for p in pairs for x in p}
    pe = sum((sum(a == l for a, _ in pairs) / n) * (sum(b == l for _, b in pairs) / n) for l in labels)
    return (None if pe == 1 else (agree / n - pe) / (1 - pe)), n, agree


def two_markers(first, second):
    """first, second: {answer_id: mark row}. Per criterion: N, agreeing answers and Cohen's kappa."""
    out = OrderedDict()
    for c in CRITERIA[:4]:
        ids = [i for i in second if i in first]
        kappa, n, agree = cohen_kappa([(first[i].get(c, ""), second[i].get(c, "")) for i in ids])
        out[c] = {"N": n, "agree": agree, "kappa": kappa}
    return out


def render_two_markers(result):
    lines = ["| Criterion | Same mark | Cohen's kappa |", "|---|---|---|"]
    for c, r in result.items():
        k = "n/a" if r["kappa"] is None else f"{r['kappa']:.3f}"
        lines.append(f"| {c} | {r['agree']} of {r['N']} | {k} |")
    return "\n".join(lines) + "\n"
