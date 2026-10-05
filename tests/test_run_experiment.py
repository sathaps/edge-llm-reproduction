import csv, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import run_experiment as rx


def test_peak_rss_is_sampled_for_the_process_tree():
    code = "import time; x = bytearray(80_000_000); time.sleep(0.6)"
    rc, wall, pipe_kb, ollama_kb = rx.run_sampled([sys.executable, "-c", code], interval=0.05)
    assert rc == 0 and wall >= 0.6
    assert pipe_kb >= 70_000
    assert ollama_kb >= 0


def test_descendants_follow_parent_links():
    assert sorted(rx.descendants(1, {2: 1, 3: 2, 4: 9})) == [1, 2, 3]


def test_grid_with_repeats_writes_runs_and_resources(pdf_path, url, stub, tmp_path):
    q = tmp_path / "q.csv"
    q.write_text("id,question\nq1,How do I start the unit?\nq2,Does model Y support the load test?\n")
    exp = tmp_path / "exp.json"
    exp.write_text(json.dumps({"id": "t", "repeats": 2, "cells": [
        {"id": "A-x", "impl": "a", "model": "llama3:latest"},
        {"id": "B-x", "impl": "b", "model": "llama3:latest", "set": ["retrieval.top_k=2"]}]}))
    out = tmp_path / "res"
    assert rx.main([str(exp), "--pdf", str(pdf_path), "--out", str(out), "--ollama", url, "--questions", str(q)]) == 0
    assert "nproc" in (out / "env.txt").read_text()
    for cell in ("A-x", "B-x"):
        for rep in (1, 2):
            d = out / cell / f"rep-{rep}"
            assert (d / "run.json").exists() and (d / "answers.jsonl").exists()
    rows = list(csv.DictReader(open(out / "resources.csv")))
    assert [(r["cell"], r["rep"]) for r in rows] == [("A-x", "1"), ("A-x", "2"), ("B-x", "1"), ("B-x", "2")]
    assert all(r["exit_code"] == "0" and int(r["pipeline_peak_rss_kb"]) > 0 and r["answers"] == "2" for r in rows)
    assert {r["index_bytes_basis"] for r in rows} == {"chunks.jsonl", "index.db"}
    ret = [json.loads(l) for l in open(out / "B-x" / "rep-1" / "retrieval.jsonl")]
    assert all(len(r["retrieved"]) == 2 for r in ret)


def test_variables_are_expanded_and_unset_ones_stop_the_run(monkeypatch):
    import pytest
    monkeypatch.setenv("E2_MODEL", "mistral:latest")
    assert rx.expand("$E2_MODEL") == "mistral:latest"
    monkeypatch.delenv("E2_MAX_DISTANCE", raising=False)
    with pytest.raises(SystemExit):
        rx.expand("retrieval.max_distance=$E2_MAX_DISTANCE")


def test_experiment_files_are_well_formed():
    root = Path(__file__).resolve().parent.parent / "experiments"
    e1 = json.load(open(root / "e1.json"))
    assert len(e1["cells"]) == 6 and {c["impl"] for c in e1["cells"]} == {"a", "b"}
    assert {c["model"] for c in e1["cells"]} == {"llama3:latest", "mistral:latest", "tinyllama:latest"}
    e2 = json.load(open(root / "e2.json"))
    assert {c["impl"] for c in e2["cells"]} == {"b"}
    assert [c["id"] for c in e2["cells"]][:1] == ["base"] and len(e2["cells"]) == 14


def test_cell_filter_runs_only_the_named_cells(pdf_path, url, stub, tmp_path):
    import pytest
    q = tmp_path / "q.csv"
    q.write_text("id,question\nq1,How do I start the unit?\n")
    exp = tmp_path / "exp.json"
    exp.write_text(json.dumps({"id": "t", "repeats": 1, "cells": [
        {"id": "A-x", "impl": "a", "model": "llama3:latest"}, {"id": "A-y", "impl": "a", "model": "mistral:latest"}]}))
    out = tmp_path / "res"
    assert rx.main([str(exp), "--pdf", str(pdf_path), "--out", str(out), "--ollama", url, "--questions", str(q), "--cell", "A-y"]) == 0
    assert [r["cell"] for r in csv.DictReader(open(out / "resources.csv"))] == ["A-y"]
    assert not (out / "A-x").exists()
    with pytest.raises(SystemExit):
        rx.main([str(exp), "--pdf", str(pdf_path), "--out", str(out), "--ollama", url, "--cell", "nope"])


def test_rep_filter_runs_only_the_named_repeats(pdf_path, url, stub, tmp_path):
    q = tmp_path / "q.csv"
    q.write_text("id,question\nq1,How do I start the unit?\n")
    exp = tmp_path / "exp.json"
    exp.write_text(json.dumps({"id": "t", "repeats": 3, "cells": [{"id": "A-x", "impl": "a", "model": "llama3:latest"}]}))
    out = tmp_path / "res"
    assert rx.main([str(exp), "--pdf", str(pdf_path), "--out", str(out), "--ollama", url, "--questions", str(q), "--rep", "2", "--rep", "3"]) == 0
    assert [r["rep"] for r in csv.DictReader(open(out / "resources.csv"))] == ["2", "3"]
    assert not (out / "A-x" / "rep-1").exists()
