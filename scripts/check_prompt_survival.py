#!/usr/bin/env python3
"""Find out which part of an over-long prompt a model still sees under its default context window.

usage: check_prompt_survival.py <out-dir> <model>
The prompt has B's template. Pages are generated filler text, not manual text. Every part carries a reference code word:
the instruction head, the start and the end of each page, and the question. The question asks the model to list every
code it can read. A code that is missing from the reply was not seen. Page 1 is the page B ranks first.
Shapes: 2 pages (control, fits), then 3, 5 and 8 pages. Output: survival_<model>.csv and replies_<model>.jsonl.

A model that lists codes can miss a code that it was shown, so the listing alone does not prove that a part was cut.
The probe step asks one question per code: which code word follows a given label, for example "Reference code for page 3
start:". The label is in the question and the code word is not, so only a model that can read the part can answer.
It runs on 1, 5 and 8 pages, with a label that is not in the prompt as a negative control. The one-page prompt fits
every window and shows how reliable the answers are when nothing is cut. Output: probe_<model>.csv.
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


PROBE_SHAPES = [1, 5, 8]


def build(cfg, pages, ask=QUESTION):
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
    q = f"Reference code for the question: {mark('question')}. {ask}"
    b = cfg["b"]["grounding"]
    text = b["template"].replace("{shortest_line}", b["shortest_line"]).replace("{context}", "\n\n".join(body)).replace("{question}", q)
    return head + text, marks


LABELS = {"instructions": "Reference code for the instructions:", "question": "Reference code for the question:"}


def label_for(part):
    if part in LABELS:
        return LABELS[part]
    m = re.match(r"page (\d+) (start|end)", part)
    return f"Reference code for page {m.group(1)} {m.group(2)}:"


def probe(out_dir, model, cfg_path="config/pipelines.json"):
    """One question per code. Writes probe_<model>.csv and returns the rows."""
    cfg = json.load(open(cfg_path))
    rows = []
    for pages in PROBE_SHAPES:
        _, marks = build(cfg, pages)
        asked = [(part, word, label_for(part)) for part, word in marks] + [("not in prompt", None, "Reference code for page 99 start:")]
        for part, word, label in asked:
            ask = f'Which code word follows the text "{label}" in this message? Answer with the code word only, or none if the text is not there.'
            prompt, _ = build(cfg, pages, ask)
            r = cp.call("/api/chat", {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False,
                                      "options": {"temperature": 0, "seed": 42, "num_predict": 8}})
            reply = r["message"]["content"].strip()
            rows.append({"model": model, "pages": pages, "window": cp.window(model), "tokens_used": r["prompt_eval_count"], "part": part,
                         "in_prompt": word is not None, "correct": word is not None and word in reply.upper(),
                         "said_none": "none" in reply.lower()})
            print(json.dumps(rows[-1]), flush=True)
    with open(f"{out_dir}/probe_{model.replace(':', '_')}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return rows


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
        print(json.dumps({"pages": pages, "reply_head": reply[:160]}), flush=True)
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
    if len(sys.argv) > 3 and sys.argv[3] == "probe":
        os.makedirs(sys.argv[1], exist_ok=True)
        probe(sys.argv[1], sys.argv[2])
    else:
        run(sys.argv[1], sys.argv[2])
