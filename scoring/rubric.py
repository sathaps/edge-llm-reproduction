"""Automatic rubric scorer. It checks strings against `required_elements`; no language model is involved.

Conventions in `required_elements` (separated by `|`):
- an element written as `a~b` is met by either `a` or `b`;
- the element `ABSTAIN` means the correct answer says the manual does not cover the question.
`forbidden_elements` uses the same `|` and `~` notation. An answer that contains one of them as a whole word or phrase is
not correct and not complete, because it states what the question excludes (the other variant's value, the steps of a
procedure that does not apply). The scorer also reports whether the required elements first appear in the listed order.
"""
import re

ABSTAIN_PATTERN = re.compile(
    r"(do not|don't|doesn't|does not) know|not (covered|mentioned|specified|stated|provided|addressed)|"
    r"(cannot|can't|unable to|could not) (find|determine|answer)|no (information|mention|reference)|"
    r"(manual|document|context|text) (does not|doesn't|do not) (cover|mention|specify|state|say|contain|include|provide|address|give|list|have|offer)|"
    r"(manual|document|context|text) (gives|provides|states|lists|has|offers|contains|includes|specifies) no |"
    r"(is|are) not (in|part of) (the|this) (manual|context|provided)", re.I)
PROCEDURE_PATTERN = re.compile(r"\bstep\s*\d|(^|\s)\d+[.)]\s+[A-Z]|\bfirst\b.*\bthen\b", re.I | re.S)
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def normalise(text):
    text = (text or "").lower().replace("–", "-").replace("—", "-").replace("°", " ")
    return re.sub(r"\s+", " ", re.sub(r"[^\w.%/ -]", " ", text)).strip()


SHORT = 4  # alternatives of up to this many characters (letters and digits only) match whole words, not substrings


def alternative_met(answer_norm, alt):
    """Matching is case-insensitive on normalised text. A short alternative such as H, OFF or AUTO must be a whole word;
    a longer one matches as a substring, so `ventilat` is met by `ventilate` and `ventilation`."""
    n = normalise(alt)
    if not n:
        return False
    if len(re.sub(r"[^a-z0-9]", "", n)) <= SHORT:
        return re.search(r"(?<![\w])" + re.escape(n) + r"(?![\w])", answer_norm) is not None
    return n in answer_norm


def element_met(answer_norm, element):
    return any(alternative_met(answer_norm, alt) for alt in element.split("~") if alt.strip())


def required(question):
    return [e.strip() for e in (question.get("required_elements") or "").split("|") if e.strip()]


def forbidden(question):
    return [e.strip() for e in (question.get("forbidden_elements") or "").split("|") if e.strip()]


def whole_phrase(answer_norm, element):
    return any(re.search(r"(?<![\w])" + re.escape(normalise(alt)) + r"(?![\w])", answer_norm) for alt in element.split("~") if alt.strip())


def in_order(answer_norm, elems):
    """True when the elements that are present first appear in the order they are listed."""
    last = -1
    for e in elems:
        pos = [answer_norm.find(normalise(alt)) for alt in e.split("~") if alt.strip() and alternative_met(answer_norm, alt)]
        if not pos:
            continue
        if min(pos) < last:
            return False
        last = min(pos)
    return True


def abstained(answer):
    return bool(ABSTAIN_PATTERN.search(answer or ""))


def unsupported_numbers(answer, retrieved_text, question_text):
    """Numbers in the answer that appear neither in the retrieved text nor in the question."""
    known = set(NUMBER.findall(retrieved_text or "")) | set(NUMBER.findall(question_text or ""))
    return sorted({n for n in NUMBER.findall(answer or "") if n not in known})


def score_answer(question, answer, retrieved_text=""):
    ans = normalise(answer)
    abst = abstained(answer)
    elems = required(question)
    if elems == ["ABSTAIN"]:
        found, total = (1 if abst else 0), 1
    else:
        found, total = sum(element_met(ans, e) for e in elems), len(elems)
    banned = [e for e in forbidden(question) if whole_phrase(ans, e)]
    complete = found == total and total > 0 and not banned
    if question["category"] == "unanswerable":
        correct = "yes" if abst else "no"
    elif abst or found == 0 or banned:
        correct = "no"
    elif complete:
        correct = "yes"
    else:
        correct = "partial"
    odd = unsupported_numbers(answer, retrieved_text, question.get("question", ""))
    return {"correct": correct, "complete": "yes" if complete else "no",
            "respects_applicability": ("yes" if complete and not abst else "no") if question["category"] == "applicability" else "",
            "abstained": "yes" if abst else "no", "unsupported_content": "yes" if odd else "no",
            "elements_found": f"{found} of {total}", "forbidden_found": " | ".join(banned), "elements_in_order": "yes" if in_order(ans, elems) else "no", "gave_procedure": "yes" if PROCEDURE_PATTERN.search(answer or "") else "no",
            "numbers_not_in_context": " ".join(odd)}
