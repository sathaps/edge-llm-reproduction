import csv

COLUMNS = ["id", "category", "question", "reference_answer", "source_pages", "exclusion_pages",
           "required_elements", "verified_by", "verified_on"]
MINIMUM = {"self_contained": 5, "condition_dependent": 5, "applicability": 5, "unanswerable": 4, "table_lookup": 3}
TARGET = 8


def parse_pages(text):
    pages = set()
    for part in (text or "").replace(",", ";").split(";"):
        part = part.strip()
        if not part:
            continue
        lo, _, hi = part.partition("-")
        pages.update(range(int(lo), int(hi or lo) + 1))
    return pages


def elements(text):
    return [e.strip() for e in (text or "").split("|") if e.strip()]


def read_questions(path):
    return list(csv.DictReader(open(path, newline="")))


def verified(rows):
    return [r for r in rows if (r.get("verified_by") or "").strip()]


def validate(rows):
    errors, warnings = [], []
    if rows and set(COLUMNS) - set(rows[0]):
        return [f"missing columns: {sorted(set(COLUMNS) - set(rows[0]))}"], []
    seen = set()
    for r in rows:
        qid = r["id"]
        if qid in seen:
            errors.append(f"{qid}: duplicate id")
        seen.add(qid)
        if r["category"] not in MINIMUM:
            errors.append(f"{qid}: unknown category {r['category']!r}")
        for col in ("question", "reference_answer"):
            if not r[col].strip():
                errors.append(f"{qid}: empty {col}")
        try:
            src, exc = parse_pages(r["source_pages"]), parse_pages(r["exclusion_pages"])
        except ValueError:
            errors.append(f"{qid}: unreadable page list")
            continue
        if r["category"] == "unanswerable":
            if src:
                errors.append(f"{qid}: unanswerable question has source_pages")
        elif not src:
            errors.append(f"{qid}: no source_pages")
        if r["category"] == "applicability" and not exc:
            errors.append(f"{qid}: applicability question has no exclusion_pages")
        if r["category"] != "applicability" and exc:
            warnings.append(f"{qid}: exclusion_pages on a non-applicability question")
        if not elements(r["required_elements"]):
            errors.append(f"{qid}: no required_elements")
    for cat, minimum in MINIMUM.items():
        n = sum(1 for r in rows if r["category"] == cat)
        if n < minimum:
            errors.append(f"{cat}: {n} questions, minimum {minimum}")
        elif n < TARGET:
            warnings.append(f"{cat}: {n} questions, target {TARGET}")
    return errors, warnings


if __name__ == "__main__":
    import sys
    errs, warns = validate(read_questions(sys.argv[1]))
    for w in warns:
        print("warning:", w)
    for e in errs:
        print("error:", e)
    sys.exit(1 if errs else 0)
