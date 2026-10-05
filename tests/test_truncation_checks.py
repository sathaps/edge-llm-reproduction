import csv, hashlib, importlib, json, os, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check_embedding_truncation as ce
import check_prompt_truncation as cp
import find_model_tag as ft


@pytest.fixture
def pages_dir(tmp_path):
    d = tmp_path / "pages"
    d.mkdir()
    for i in range(30):
        pad = "z" * 10 if i % 2 else ""  # long words give short pages that still pass the length filter
        words = [f"w{i}x{j}{pad}" for j in range(40 + (i % 9) * 80)]  # 40 to 680 words
        (d / f"{i + 1:03d}.txt").write_text(" ".join(words))
    return d


@pytest.fixture
def emulating(stub, monkeypatch, url):
    stub.emulate_context = True
    monkeypatch.setattr(cp, "call", lambda path, body: __import__("json").load(__import__("urllib.request").request.urlopen(
        __import__("urllib.request").request.Request(url + path, __import__("json").dumps(body).encode(), {"Content-Type": "application/json"}))))
    return stub


def patch_urls(monkeypatch, url):
    import json, urllib.request
    real = urllib.request.urlopen

    def opener(req, timeout=None):
        target = req if isinstance(req, str) else req.full_url
        if isinstance(req, str):
            req = target.replace("http://localhost:11434", url)
        else:
            req = urllib.request.Request(target.replace("http://localhost:11434", url), req.data, dict(req.headers))
        return real(req, timeout=timeout)
    monkeypatch.setattr(urllib.request, "urlopen", opener)


def test_prompt_truncation_table(tmp_path, stub, url, monkeypatch):
    stub.emulate_context = True
    patch_urls(monkeypatch, url)
    big = tmp_path / "big"
    big.mkdir()
    for i in range(40):
        (big / f"{i + 1:03d}.txt").write_text(" ".join(f"t{i}_{j}" for j in range(1300)) + " " + "x" * 3000)
    rows = cp.main(str(big), str(tmp_path / "out"), "llama3:latest", str(ROOT / "config/pipelines.json"))
    by = {(r["shape"], r["units"]): r for r in rows}
    assert by[("A", 3)]["truncated"] is False and by[("A", 3)]["tokens_dropped"] == 0
    assert by[("B", 1)]["truncated"] is False and by[("B", 1)]["tokens_used"] == by[("B", 1)]["tokens_offered"]
    assert by[("B", 8)]["truncated"] is True
    assert by[("B", 8)]["tokens_used"] == 4096 == by[("B", 8)]["window_default"]
    assert by[("B", 8)]["window_raised"] == 8192
    assert by[("B", 8)]["tokens_dropped"] == by[("B", 8)]["tokens_offered"] - 4096
    assert (tmp_path / "out" / "prompt_truncation_llama3_latest.csv").exists()
    # the single raised pass cannot count beyond the trained length, the piecewise count can
    assert by[("B", 8)]["tokens_single_raised_pass"] == 8192 and by[("B", 8)]["tokens_offered"] > 8192
    assert by[("B", 1)]["tokens_single_raised_pass"] == by[("B", 1)]["tokens_offered"]


def test_prompt_truncation_for_a_model_whose_trained_length_equals_its_window(tmp_path, stub, url, monkeypatch):
    stub.emulate_context = True
    patch_urls(monkeypatch, url)
    big = tmp_path / "big"
    big.mkdir()
    for i in range(40):
        (big / f"{i + 1:03d}.txt").write_text(" ".join(f"t{i}_{j}" for j in range(1300)) + " " + "x" * 3000)
    rows = cp.main(str(big), str(tmp_path / "out"), "tinyllama:latest", str(ROOT / "config/pipelines.json"))
    by = {(r["shape"], r["units"]): r for r in rows}
    assert by[("B", 5)]["window_raised"] == 2048 and by[("B", 5)]["tokens_single_raised_pass"] == 2048
    assert by[("B", 5)]["tokens_offered"] > 4000 and by[("B", 5)]["truncated"] is True


def test_embedding_truncation_table(tmp_path, stub, url, pages_dir, monkeypatch):
    stub.emulate_context = True
    patch_urls(monkeypatch, url)
    ce.main(str(pages_dir), str(tmp_path / "out"), ["all-minilm:latest"])
    summary = list(csv.DictReader(open(tmp_path / "out" / "embedding_truncation.csv")))[0]
    assert summary["window_in_effect"] == "256" and summary["special_tokens_per_input"] == "2"
    assert int(summary["pages_tested"]) >= 10 and float(summary["median_tokens_used"]) <= 256
    assert int(summary["pages_cut"]) > 0 and float(summary["median_cos_full_vs_prefix"]) == pytest.approx(1.0, abs=1e-5)
    assert float(summary["median_cos_full_vs_tail"]) < 0.5
    detail = list(csv.DictReader(open(tmp_path / "out" / "embedding_truncation_pages.csv")))
    long_pages = [r for r in detail if int(r["tokens_offered"]) > 256]
    assert long_pages and all(int(r["tokens_used"]) == 256 for r in long_pages)
    short = [r for r in detail if int(r["tokens_offered"]) <= 256]
    assert short and all(int(r["tokens_used"]) == int(r["tokens_offered"]) for r in short)


def test_tag_search_marks_the_matching_tag(tmp_path, url, monkeypatch, capsys):
    monkeypatch.setattr(ft, "REGISTRY", url + "/v2/library")
    want = hashlib.sha256(b"manifest of mistral:v0.2").hexdigest()[:12]
    ft.main("mistral", want, str(tmp_path / "tags.csv"), [f"latest={hashlib.sha256(b'manifest of mistral:latest').hexdigest()[:12]}"])
    rows = list(csv.DictReader(open(tmp_path / "tags.csv")))
    assert [r["tag"] for r in rows if r["matches_wanted"] == "True"] == ["v0.2"]
    out = capsys.readouterr().out
    assert "self-check latest" in out and "ok" in out and "tags with id" in out


def write_run(d, rows, model="llama3:latest"):
    d.mkdir()
    (d / "run.json").write_text(json.dumps({"model": model}))
    (d / "answers.jsonl").write_text("".join(json.dumps(r["answer"]) + "\n" for r in rows))
    (d / "prompts.jsonl").write_text("".join(json.dumps(r["prompt"]) + "\n" for r in rows))


def test_count_offered_marks_only_cut_prompts(tmp_path, stub, url, monkeypatch):
    import count_offered
    stub.emulate_context = True
    long_text = " ".join(f"w{i}" for i in range(6000))
    rows = []
    for qid, text, used in [("short", "w " * 50, 53), ("long", long_text, 4096), ("fits", " ".join(f"w{i}" for i in range(3000)), 3003)]:
        rows.append({"answer": {"question_id": qid, "prompt_eval_count": used, "context_length": 4096},
                     "prompt": {"question_id": qid, "messages": [{"role": "user", "content": text}]}})
    write_run(tmp_path / "run", rows)
    out = {a["question_id"]: a for a in count_offered.annotate(tmp_path / "run", url)}
    assert out["short"]["prompt_truncated"] is False and out["short"]["tokens_offered"] == 53
    assert out["fits"]["prompt_truncated"] is False and out["fits"]["tokens_dropped"] == 0
    assert out["long"]["prompt_truncated"] is True and out["long"]["tokens_offered"] > 4096
    assert out["long"]["tokens_dropped"] == out["long"]["tokens_offered"] - 4096
    assert not (tmp_path / "run" / "prompts.jsonl").exists()
    assert json.loads(open(tmp_path / "run" / "answers.jsonl").readline())["tokens_offered"] == 53


def test_survival_table_follows_what_the_model_lists(tmp_path, stub, url, monkeypatch):
    import check_prompt_survival as cs
    stub.emulate_context = True
    patch_urls(monkeypatch, url)

    def reply(path, body):
        text = body["messages"][-1]["content"]
        words = text.split()
        tail = " ".join(words[len(words) // 2:])  # a model that keeps the second half
        return "\n".join(w for w in cs.WORDS if w in tail)
    stub.reply = reply
    rows = cs.run(str(tmp_path / "out"), "llama3:latest", str(ROOT / "config/pipelines.json"))
    by = {(r["pages"], r["part"]): r for r in rows}
    assert by[(2, "question")]["listed_by_model"] is True and by[(2, "question")]["truncated"] is False
    assert by[(8, "instructions")]["truncated"] is True and by[(8, "instructions")]["listed_by_model"] is False
    assert by[(8, "question")]["listed_by_model"] is True
    assert len([r for r in rows if r["pages"] == 8]) == 2 + 2 * 8


def test_embedding_retrieval_counts_and_prints_no_text(tmp_path, stub, url, monkeypatch, capsys):
    import check_embedding_retrieval as cr
    stub.emulate_context = True
    patch_urls(monkeypatch, url)
    d = tmp_path / "pages"
    d.mkdir()
    for i in range(12):
        sentences = [f"Page {i} sentence {j} mentions item{i}x{j} and part{i}y{j} here." for j in range(60)]
        (d / f"{i + 1:03d}.txt").write_text(" ".join(sentences))
    rows = cr.run(str(d), str(tmp_path / "out"), ["all-minilm:latest"])
    by = {r["group"]: r for r in rows}
    assert by["inside"]["queries"] > 0 and by["beyond"]["queries"] > 0
    assert by["inside"]["hit_top5"] <= by["inside"]["queries"]
    assert "mentions" not in capsys.readouterr().out
    detail = open(tmp_path / "out" / "embedding_retrieval_queries.csv").read()
    assert "mentions" not in detail


def test_structure_finds_procedures_that_cross_pages_and_tables(tmp_path):
    import manual_structure as ms
    d = tmp_path / "pages"
    d.mkdir()
    (d / "001.txt").write_text("Starting. Before you start, make sure the valve is open.\n1. Close the breaker.\n2. Set the selector.\n3. Press START.\n")
    (d / "002.txt").write_text("4. Release the button.\n5. Check the oil pressure.\nTable 4-1 Limits\nOil pressure minimum 20 psi trip 15 psi\n")
    (d / "003.txt").write_text("Overspeed trip 2100 rpm. This screen applies only to electronic engines.\n")
    res = ms.main(str(d), str(tmp_path / "out"))
    assert [(p["start_page"], p["end_page"], p["steps"], p["crosses_page"]) for p in res["procedures"]] == [(1, 2, 5, True)]
    assert res["procedures"][0]["prerequisite_words"] >= 1
    assert res["tables"][0]["label"].lower() == "table 4-1" and res["tables"][0]["value_cells"] >= 1
    assert [l["page"] for l in res["limits"]] == [2, 3] and res["limits"][1]["trip_or_alarm_lines"] == 1
    assert [a["page"] for a in res["applicability"]] == [3]
    assert "label" not in res["applicability"][0]


def test_probe_asks_for_the_code_after_a_label_and_has_a_negative_control(tmp_path, stub, url, monkeypatch):
    import re, check_prompt_survival as cs
    stub.emulate_context = True
    patch_urls(monkeypatch, url)

    def reply(path, body):
        text = body["messages"][-1]["content"]
        label = re.search(r'follows the text "([^"]+)"', text).group(1)
        words = text.split()
        tail = " ".join(words if len(words) < 3000 else words[len(words) // 2:])  # a model that keeps the second half of a long prompt
        m = re.search(re.escape(label) + r" (\w+)\.", tail)
        return m.group(1) if m and label != "Reference code for page 99 start:" else "none"
    stub.reply = reply
    rows = cs.probe(str(tmp_path), "llama3:latest", str(ROOT / "config/pipelines.json"))
    one = [r for r in rows if r["pages"] == 1]
    assert len(one) == 4 + 1 and all(r["correct"] for r in one if r["in_prompt"])
    assert [r["said_none"] for r in rows if not r["in_prompt"]] == [True, True, True]
    eight = {r["part"]: r for r in rows if r["pages"] == 8}
    assert not eight["instructions"]["correct"] and eight["page 8 end"]["correct"] and eight["question"]["correct"]
    assert (tmp_path / "probe_llama3_latest.csv").exists()
