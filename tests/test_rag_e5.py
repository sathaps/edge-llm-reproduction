import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipelines" / "e5_prompt"))
import argparse

import rag_e5


def args(pdf, url, q, out):
    return argparse.Namespace(pdf=str(pdf), model="mistral:latest", ollama=url, questions=str(q), question=None, limit=None, out=str(out))


def test_manual_text_goes_in_the_system_prompt_with_default_options(pdf_path, url, stub, tmp_path):
    q = tmp_path / "q.csv"
    q.write_text("id,question\nq1,How do I start the unit?\n")
    stub.prompt_tokens = 4000
    rag_e5.run(args(pdf_path, url, q, tmp_path / "out"))
    chat = [b for p, b in stub.requests if p == "/api/chat"]
    assert len(chat) == 1
    system = chat[0]["messages"][0]["content"]
    assert system.startswith("Answer the user's questions") and "Press START and hold for five seconds" in system and "Disconnect the battery." in system
    assert chat[0]["options"] == {"temperature": 0, "seed": 42}
    a = [json.loads(l) for l in open(tmp_path / "out" / "answers.jsonl")][0]
    assert a["prompt_eval_count"] == 4000 and a["context_length"] == 4096
    run = json.load(open(tmp_path / "out" / "run.json"))
    assert run["experiment"] == "e5" and run["manual_chars"] > 100
