import csv, json, shutil, subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(shutil.which("dotnet") is None, reason="dotnet is not installed")

OK = '{"kind":"SetSetpoint","tag":"RateSetpoint","value":8.2,"rationale":"stub"}'


def stub_reply(path, body):
    text = body["messages"][-1]["content"]
    if "pressure setpoint to 9500" in text:
        return '{"kind":"SetSetpoint","tag":"PressureSetpoint","value":9500}'
    if "Inhibit the high pressure trip" in text:
        return '{"kind":"InhibitTrip","tag":"HighPressureTrip"}'
    if "Standby" in text:
        return '```json\n{"kind":"ChangeMode","tag":"UnitMode","mode":"Standby"}\n```'
    if "Open valve" in text:
        return "I will open the valve now."
    return OK


@pytest.fixture(scope="module")
def dll(tmp_path_factory):
    out = tmp_path_factory.mktemp("modelrun_build")
    subprocess.run(["dotnet", "build", str(ROOT / "gate/modelrun"), "-o", str(out), "-v", "q"], check=True, capture_output=True)
    return out / "ModelRun.dll"


def run(dll, url, requests, tmp_path):
    out = tmp_path / "out"
    r = subprocess.run(["dotnet", str(dll), "--requests", str(ROOT / requests), "--model", "stub", "--ollama", url, "--out", str(out),
                        "--schema", str(ROOT / "gate/proposals/schema_prompt.txt")], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-1500:] + r.stdout[-1500:]
    return out, r.stdout


def test_counts_for_the_operator_requests(dll, url, stub, tmp_path):
    stub.reply = stub_reply
    out, stdout = run(dll, url, "gate/proposals/requests.json", tmp_path)
    s = json.load(open(out / "gate_model_summary.json"))
    assert s["total"] == 24
    assert s["by_reason_code"] == {"ABOVE_HIGH_LIMIT": 1, "ACCEPTED": 20, "SCHEMA_INVALID": 2, "TRIP_INHIBIT_FORBIDDEN": 1}
    assert s["parsed"] == 22 and s["accepted"] == 20 and s["refused"] == 4
    assert s["accepted_outside_envelope"] == 0
    assert "22 of 24 parsed" in stdout


def test_rows_and_schema_prompt_reach_the_model(dll, url, stub, tmp_path):
    stub.reply = stub_reply
    out, _ = run(dll, url, "gate/proposals/adversarial.json", tmp_path)
    rows = list(csv.DictReader(open(out / "gate_model.csv")))
    assert len(rows) == 10 and {r["group"] for r in rows} == {"adversarial"}
    assert [r["request_id"] for r in rows][:2] == ["A01", "A02"]
    chat = [b for p, b in stub.requests if p == "/api/chat"]
    assert chat[0]["messages"][0]["content"].startswith("You are the planning layer") and chat[0]["options"] == {"temperature": 0, "seed": 42}


def test_an_out_of_envelope_proposal_the_gate_wrongly_accepted_would_be_counted(dll, url, stub, tmp_path):
    # The stub proposes a value the envelope forbids on every request. The gate refuses all of them, so the count stays zero.
    stub.reply = lambda path, body: '{"kind":"SetSetpoint","tag":"PressureSetpoint","value":12000}'
    out, _ = run(dll, url, "gate/proposals/adversarial.json", tmp_path)
    s = json.load(open(out / "gate_model_summary.json"))
    assert s["accepted"] == 0 and s["accepted_outside_envelope"] == 0 and s["by_reason_code"] == {"ABOVE_HIGH_LIMIT": 10}
