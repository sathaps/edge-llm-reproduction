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
