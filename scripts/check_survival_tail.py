#!/usr/bin/env python3
"""Check by token arithmetic where the cut falls in an over-long prompt, without relying on what the model says.

usage: check_survival_tail.py <out-dir> <model>
Part 1 (B's shape). B's template with eight generated pages, a code word every 10 sentences. One question per code word
asks which code word follows its label. The first code of the longest run of correct answers that reaches the end of the
prompt is the first one the model reads. The prompt text from that label to the end is then sent alone, with the same
window and num_predict 1, and its prompt_eval_count is compared with the prompt_eval_count of the full prompt. The tail
from the last code that was not read is sent too. If the model starts reading where the cut falls, the first tail is
close to the full count and the second is not smaller than it.
Part 2 (A's shape). A system message with a code word, then one user message that starts with the question and a code
word and is followed by the same pages. Questions ask for the two codes.
Output: tail_<model>.csv and a line per probe.
"""
import csv, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_prompt_survival as cs
import check_prompt_truncation as cp

PAGES = 8
EVERY = 10


def code(i):
    return f"{cs.WORDS[i % len(cs.WORDS)]}{i}"


def dense_pages(first=0):
    """Pages of filler with a numbered code every EVERY sentences. Returns the text and the numbers used."""
    out, n = [], first
    for p in range(1, PAGES + 1):
        sentences = cs.filler(p, cs.PAGE_CHARS).split(". ")
        parts = []
        for k, s in enumerate(sentences):
            parts.append(s)
            if (k + 1) % EVERY == 0:
                parts.append(f"Reference code for part {n}: {code(n)}.")
                n += 1
        out.append(" ".join(parts))
    return "\n\n".join(out), list(range(first, n))


def ask_for(label):
    return f'Which code word follows the text "{label}" in this message? Answer with the code word only, or none if the text is not there.'


def chat(model, messages):
    r = cp.call("/api/chat", {"model": model, "messages": messages, "stream": False,
                              "options": {"temperature": 0, "seed": 42, "num_predict": 8}})
    return r["message"]["content"].strip(), r["prompt_eval_count"]


def count_only(model, text):
    r = cp.call("/api/chat", {"model": model, "messages": [{"role": "user", "content": text}], "stream": False,
                              "options": {"temperature": 0, "seed": 42, "num_predict": 1}})
    return r["prompt_eval_count"]


def part1(model, cfg, rows):
    b = cfg["b"]["grounding"]
    context, numbers = dense_pages()

    def prompt(n):
        return b["template"].replace("{shortest_line}", b["shortest_line"]).replace("{context}", context).replace("{question}", ask_for(f"Reference code for part {n}:"))

    results = {}
    for n in numbers:
        reply, used = chat(model, [{"role": "user", "content": prompt(n)}])
        results[n] = code(n) in reply.upper().replace(" ", "")
        print(json.dumps({"model": model, "part": 1, "code_no": n, "correct": results[n], "tokens_used": used}), flush=True)
    first = len(numbers)
    for n in reversed(numbers):
        if not results[n]:
            break
        first = n
    window = cp.window(model)
    full_used = chat(model, [{"role": "user", "content": prompt(first)}])[1] if first < len(numbers) else None
    checks = [("first code read", first)] + ([("last code not read", first - 1)] if first > 0 else [])
    for name, n in checks:
        text = prompt(n)
        label = f"Reference code for part {n}: {code(n)}."
        tail = text[text.index(label):]
        row = {"model": model, "check": name, "code_no": n, "window": window, "full_prompt_used": full_used,
               "tail_chars": len(tail), "tail_prompt_eval_count": count_only(model, tail),
               "codes_read": sum(results.values()), "codes_total": len(numbers)}
        rows.append(row)
        print(json.dumps(row), flush=True)


def part2(model, cfg, rows):
    context, _ = dense_pages(first=100)
    sys_text = f"Reference code for the system message: {code(200)}. " + cfg["a"]["grounding"]["system"]
    user = f"Reference code for the question: {code(201)}. " + "How is the unit started?" + "\n\nRelevant Context:\n" + context
    for label, c in [("Reference code for the system message:", code(200)), ("Reference code for the question:", code(201))]:
        q = user + "\n\n" + ask_for(label)
        reply, used = chat(model, [{"role": "system", "content": sys_text}, {"role": "user", "content": q}])
        row = {"model": model, "check": "A shape: " + label, "window": cp.window(model), "full_prompt_used": used, "correct": c in reply.upper().replace(" ", "")}
        rows.append(row)
        print(json.dumps(row), flush=True)


def main(out_dir, model, cfg_path="config/pipelines.json"):
    os.makedirs(out_dir, exist_ok=True)
    cfg = json.load(open(cfg_path))
    rows = []
    part1(model, cfg, rows)
    part2(model, cfg, rows)
    keys = sorted({k for r in rows for k in r})
    with open(f"{out_dir}/tail_{model.replace(':', '_')}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main(*sys.argv[1:3])
