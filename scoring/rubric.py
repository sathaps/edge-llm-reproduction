"""Automatic rubric scorer. It checks strings against `required_elements`; no language model is involved.

Conventions in `required_elements` (separated by `|`):
- an element written as `a~b` is met by either `a` or `b`;
- the element `ABSTAIN` means the correct answer says the manual does not cover the question.
"""
import re

ABSTAIN_PATTERN = re.compile(
    r"(do not|don't|doesn't|does not) know|not (covered|mentioned|specified|stated|provided|addressed)|"
    r"(cannot|can't|unable to|could not) (find|determine|answer)|no (information|mention|reference)|"
    r"(manual|document|context|text) (does not|doesn't|do not) (cover|mention|specify|state|say|contain|include|provide|address)|"
    r"(is|are) not (in|part of) (the|this) (manual|context|provided)", re.I)
PROCEDURE_PATTERN = re.compile(r"\bstep\s*\d|(^|\s)\d+[.)]\s+[A-Z]|\bfirst\b.*\bthen\b", re.I | re.S)
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def normalise(text):
    text = (text or "").lower().replace("–", "-").replace("—", "-").replace("°", " ")
    return re.sub(r"\s+", " ", re.sub(r"[^\w.%/ -]", " ", text)).strip()


def element_met(answer_norm, element):
    return any(normalise(alt) in answer_norm for alt in element.split("~") if alt.strip())


def required(question):
    return [e.strip() for e in (question.get("required_elements") or "").split("|") if e.strip()]


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
    complete = found == total and total > 0
    if question["category"] == "unanswerable":
        correct = "yes" if abst else "no"
    elif abst or found == 0:
        correct = "no"
    elif complete:
        correct = "yes"
    else:
        correct = "partial"
    odd = unsupported_numbers(answer, retrieved_text, question.get("question", ""))
    return {"correct": correct, "complete": "yes" if complete else "no",
            "respects_applicability": ("yes" if complete and not abst else "no") if question["category"] == "applicability" else "",
            "abstained": "yes" if abst else "no", "unsupported_content": "yes" if odd else "no",
            "elements_found": f"{found} of {total}", "gave_procedure": "yes" if PROCEDURE_PATTERN.search(answer or "") else "no",
            "numbers_not_in_context": " ".join(odd)}
