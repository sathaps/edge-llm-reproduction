import csv, json
import marks, retrieval_score, blind_export, questions as qmod


def question(qid, cat, src="2", exc="", elems="a|b", by="x"):
    return {"id": qid, "category": cat, "question": f"question {qid}", "reference_answer": f"reference {qid}", "source_pages": src,
            "exclusion_pages": exc, "required_elements": elems, "verified_by": by, "verified_on": "2026-01-01" if by else ""}


def full_set(n=8):
    cats = list(qmod.MINIMUM)
    rows = []
    for c in cats:
        for i in range(n):
            rows.append(question(f"{c}-{i}", c, src="" if c == "unanswerable" else "3", exc="4" if c == "applicability" else ""))
    return rows


def test_parse_pages():
    assert qmod.parse_pages("12;14-15") == {12, 14, 15}
    assert qmod.parse_pages("") == set()
    assert qmod.parse_pages("3, 5") == {3, 5}


def test_validate_accepts_a_full_set():
    assert qmod.validate(full_set()) == ([], [])


def test_validate_reports_each_problem():
    rows = full_set(5)
    rows[0]["category"] = "other"
    rows[1]["source_pages"] = ""
    rows[2]["id"] = rows[3]["id"]
    errs, warns = qmod.validate(rows)
    joined = " ".join(errs)
    assert "unknown category" in joined and "no source_pages" in joined and "duplicate id" in joined
    assert any("target 8" in w for w in warns)


def test_validate_flags_missing_applicability_exclusion_and_small_categories():
    rows = [r for r in full_set(8) if r["category"] != "table_lookup"]
    for r in rows:
        if r["category"] == "applicability":
            r["exclusion_pages"] = ""
    errs, _ = qmod.validate(rows)
    assert any("no exclusion_pages" in e for e in errs) and any("table_lookup: 0 questions" in e for e in errs)


def retrieval(qid, *page_sets):
    return {"question_id": qid, "retrieved": [{"chunk_id": f"c{i}", "pages": p, "score": 1.0} for i, p in enumerate(page_sets)]}


def test_retrieval_hits_exclusions_and_unverified_are_handled():
    qs = [question("s1", "self_contained", src="3;4"), question("a1", "applicability", src="5", exc="9"),
          question("u1", "unanswerable", src=""), question("s2", "self_contained", by="")]
    rows = retrieval_score.score_run(qs, [retrieval("s1", [1], [3]), retrieval("a1", [5, 6]), retrieval("u1"), retrieval("s2", [3])], "cfg")
    by = {r["question_id"]: r for r in rows}
    assert set(by) == {"s1", "a1", "u1"}
    assert by["s1"]["any_reference_page"] and not by["s1"]["all_reference_pages"] and by["s1"]["first_hit_rank"] == 2
    assert by["a1"]["any_reference_page"] and by["a1"]["exclusion_retrieved"] is False
    assert by["u1"]["any_reference_page"] is None and by["u1"]["n_retrieved"] == 0
    s = retrieval_score.summarise(rows)
    assert s["self_contained"]["N"] == 1 and s["self_contained"]["any"] == 1 and s["self_contained"]["all"] == 0
    assert s["applicability"]["exclusion"] == 0 and s["applicability"]["exclusion_N"] == 1
    assert s["unanswerable"]["returned_nothing"] == 1


def make_run(tmp_path, name, answers):
    d = tmp_path / name
    d.mkdir()
    with open(d / "answers.jsonl", "w") as f:
        for qid, a in answers.items():
            f.write(json.dumps({"question_id": qid, "answer": a}) + "\n")
    with open(d / "retrieval.jsonl", "w") as f:
        for qid in answers:
            f.write(json.dumps({"question_id": qid, "retrieved": [{"chunk_id": "c0", "pages": [3], "score": 1.0}]}) + "\n")
    with open(d / "chunks.jsonl", "w") as f:
        f.write(json.dumps({"chunk_id": "c0", "pages": [3], "text": f"text of {name}"}) + "\n")
    return d


def test_blind_export_shuffles_hides_configuration_and_round_trips(tmp_path):
    qs = [question(f"q{i}", "self_contained", elems="alpha|beta") for i in range(6)]
    answers = {f"q{i}": f"alpha and beta {i}" if i % 2 else "I do not know" for i in range(6)}
    runs = {"A-llama3": make_run(tmp_path, "ra", answers), "B-llama3": make_run(tmp_path, "rb", answers)}
    out = tmp_path / "marking"
    key = blind_export.export(runs, qs, out, seed=7)
    key2 = blind_export.export(runs, qs, tmp_path / "again", seed=7)
    assert key == key2
    assert json.load(open(out / "export.json")) == {"seed": 7, "rows": 12}

    blind = marks.read_csv(out / "sheet_blind.csv")
    assert len(blind) == 12 and len({r["answer_id"] for r in blind}) == 12
    text = open(out / "sheet_blind.csv").read() + open(out / "sheet_support.csv").read() + open(out / "suggestions.csv").read()
    assert "A-llama3" not in text and "B-llama3" not in text and "ra" not in {r["answer_id"] for r in blind}
    configs_in_order = [r["config_id"] for r in marks.read_csv(out / "key.csv")]
    assert configs_in_order != sorted(configs_in_order)

    sugg = {r["answer_id"]: r for r in marks.read_csv(out / "suggestions.csv")}
    for r in blind:
        s = sugg[r["answer_id"]]
        assert (s["suggested_abstained"] == "yes") == ("do not know" in r["answer"])
        assert (s["suggested_complete"] == "yes") == ("alpha and beta" in r["answer"])

    for r in blind:
        r["correct"] = "yes" if "alpha" in r["answer"] else "no"
        r["complete"] = "yes" if "alpha" in r["answer"] else "no"
    for name, rows in (("sheet_blind.csv", blind),):
        with open(out / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    marked = marks.join_marks(marks.read_csv(out / "sheet_blind.csv"), marks.read_csv(out / "sheet_support.csv"), marks.read_csv(out / "key.csv"))
    assert len(marked) == 12
    table = marks.counts(marked)
    assert table[("A-llama3", "self_contained")] == {"N": 6, "yes": 3, "partial": 0}
    assert table[("B-llama3", "self_contained")]["N"] == 6
    configs, rows = marks.outcomes_by_question(marked)
    assert configs == ["A-llama3", "B-llama3"] and len(rows) == 6
    assert all(r["A-llama3"] == r["B-llama3"] for r in rows)


def test_unmarked_rows_are_left_out(tmp_path):
    qs = [question("q0", "self_contained")]
    runs = {"A": make_run(tmp_path, "ra", {"q0": "alpha"})}
    out = tmp_path / "m"
    blind_export.export(runs, qs, out, seed=1)
    marked = marks.join_marks(marks.read_csv(out / "sheet_blind.csv"), marks.read_csv(out / "sheet_support.csv"), marks.read_csv(out / "key.csv"))
    assert marked == []


def test_export_skips_unverified_questions(tmp_path):
    qs = [question("q0", "self_contained", by=""), question("q1", "self_contained")]
    runs = {"A": make_run(tmp_path, "ra", {"q0": "x", "q1": "y"})}
    blind_export.export(runs, qs, tmp_path / "m", seed=1)
    assert [r["question_id"] for r in marks.read_csv(tmp_path / "m" / "key.csv")] == ["q1"]


def test_command_line_round_trip(tmp_path):
    import run_scoring
    qs = full_set(5)
    with open(tmp_path / "q.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=qmod.COLUMNS)
        w.writeheader()
        w.writerows(qs)
    assert run_scoring.main(["validate", str(tmp_path / "q.csv")]) == 0
    runs = {"A": make_run(tmp_path, "ra", {r["id"]: "alpha beta" for r in qs[:3]})}
    assert run_scoring.main(["retrieval", str(tmp_path / "q.csv"), str(tmp_path / "ret.csv"), f"A={runs['A']}"]) == 0
    assert (tmp_path / "ret.csv").read_text().startswith("config_id,question_id,category")
    assert run_scoring.main(["export", str(tmp_path / "q.csv"), str(tmp_path / "m"), "3", f"A={runs['A']}"]) == 0
    assert run_scoring.main(["join", str(tmp_path / "m"), str(tmp_path / "j")]) == 0


def test_summary_tables_show_repeats_and_mark_differences():
    import summary_tables as st
    rows = []
    for rep, correct in (("1", 5), ("2", 5), ("3", 6)):
        for i in range(8):
            rows.append({"config_id": f"A-llama3@{rep}", "category": "self_contained", "correct": "yes" if i < correct else "no"})
    for rep in ("1", "2"):
        for i in range(8):
            rows.append({"config_id": f"B-llama3@{rep}", "category": "self_contained", "correct": "yes" if i < 3 else "no"})
    table = st.correct_table(rows)
    lines = table.splitlines()
    assert lines[0].startswith("| Configuration | self_contained | condition_dependent")
    a = next(l for l in lines if l.startswith("| A-llama3"))
    b = next(l for l in lines if l.startswith("| B-llama3"))
    assert "5 of 8 / 5 of 8 / 6 of 8*" in a and "3 of 8 / 3 of 8 |" in b and "*" not in b
    assert a.count("n/a") == 4


def test_retrieval_table_leaves_out_unanswerable_and_exclusion_table_counts_applicability():
    import summary_tables as st
    rows = [{"config_id": "A@1", "category": "applicability", "any_reference_page": True, "exclusion_retrieved": False},
            {"config_id": "A@1", "category": "applicability", "any_reference_page": True, "exclusion_retrieved": True},
            {"config_id": "A@1", "category": "unanswerable", "any_reference_page": None, "exclusion_retrieved": None}]
    ret = st.retrieval_table(rows).splitlines()[-1]
    exc = st.exclusion_table(rows).splitlines()[-1]
    assert "2 of 2" in ret and ret.count("n/a") == 4
    assert "1 of 2" in exc and exc.count("n/a") == 4
