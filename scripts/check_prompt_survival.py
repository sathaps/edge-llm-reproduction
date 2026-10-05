#!/usr/bin/env python3
"""Find out which part of an over-long prompt a model still sees under its default context window.

usage: check_prompt_survival.py <out-dir> <model>
The prompt has B's template. Pages are generated filler text, not manual text. Every part carries a reference code word:
the instruction head, the start and the end of each page, and the question. The question asks the model to list every
code it can read. A code that is missing from the reply was not seen. Page 1 is the page B ranks first.
Shapes: 2 pages (control, fits), then 3, 5 and 8 pages. Output: survival_<model>.csv and replies_<model>.jsonl.
"""
import csv, json, os, random, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_prompt_truncation as cp

WORDS = ["AMBER", "BASALT", "CEDAR", "DAHLIA", "EMBER", "FJORD", "GRANITE", "HAZEL", "INDIGO", "JASPER", "KESTREL", "LICHEN",
         "MARBLE", "NETTLE", "OPAL", "PEBBLE", "QUARTZ", "RUSSET", "SORREL", "TUNDRA", "UMBER", "VELVET", "WILLOW", "YARROW",
         "ZEPHYR", "COBALT", "DRIFT", "FALCON", "GARNET", "HERON"]
SHAPES = [2, 3, 5, 8]
PAGE_CHARS = 3000
QUESTION = "List every reference code that you can read anywhere in this message, one per line, as the code word only."


def filler(seed, chars):
    rng = random.Random(seed)
    nouns = ["valve", "pump", "sensor", "gasket", "bracket", "filter", "relay", "gauge"]
    adjs = ["clean", "dry", "tight", "aligned", "labelled", "isolated"]
    out, n = [], 0
    while n < chars:
        s = f"Step {rng.randint(1, 99)} of procedure {rng.randint(100, 999)} needs a {rng.choice(adjs)} {rng.choice(nouns)} at {rng.randint(10, 99)} bar."
        out.append(s)
        n += len(s) + 1
    return " ".join(out)


def build(cfg, pages):
    """Returns the prompt and the list of (position label, code word) in prompt order."""
    codes = iter(WORDS)
    marks = []

    def mark(label):
        word = next(codes)
        marks.append((label, word))
        return word

    head = f"Reference code for the instructions: {mark('instructions')}.\n"
    body = []
    for i in range(1, pages + 1):
        start = mark(f"page {i} start")
        body.append(f"Reference code for page {i} start: {start}. " + filler(i, PAGE_CHARS) + f" Reference code for page {i} end: {mark(f'page {i} end')}.")
    q = f"Reference code for the question: {mark('question')}. {QUESTION}"
    b = cfg["b"]["grounding"]
    text = b["template"].replace("{shortest_line}", b["shortest_line"]).replace("{context}", "\n\n".join(body)).replace("{question}", q)
    return head + text, marks


def run(out_dir, model, cfg_path="config/pipelines.json"):
    os.makedirs(out_dir, exist_ok=True)
    cfg = json.load(open(cfg_path))
    overhead = cp.template_overhead(model)
    rows, replies = [], []
    for pages in SHAPES:
        prompt, marks = build(cfg, pages)
        messages = [{"role": "user", "content": prompt}]
        r = cp.call("/api/chat", {"model": model, "messages": messages, "stream": False,
                                  "options": {"temperature": 0, "seed": 42, "num_predict": 200}})
        window = cp.window(model)
        offered = cp.offered_by_pieces(model, messages, overhead)[0]
        reply = r["message"]["content"]
        seen = set(re.findall(r"[A-Za-z]+", reply.upper()))
        replies.append({"model": model, "pages": pages, "reply": reply})
        for pos, (label, word) in enumerate(marks, 1):
            rows.append({"model": model, "pages": pages, "window": window, "tokens_offered": offered, "tokens_used": r["prompt_eval_count"],
                         "truncated": offered > window, "position": pos, "part": label, "listed_by_model": word in seen})
        extra = sorted(seen & set(WORDS) - {w for _, w in marks})
        print(json.dumps({"pages": pages, "window": window, "offered": offered, "used": r["prompt_eval_count"],
                          "listed": [l for l, w in marks if w in seen], "not_listed": [l for l, w in marks if w not in seen],
                          "codes_listed_that_are_not_in_the_prompt": extra}), flush=True)
    stem = model.replace(":", "_")
    with open(f"{out_dir}/survival_{stem}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(f"{out_dir}/replies_{stem}.jsonl", "w") as f:
        f.writelines(json.dumps(x) + "\n" for x in replies)
    return rows


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
