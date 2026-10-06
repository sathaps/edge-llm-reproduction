import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_experiment as rx  # noqa: E402


def test_every_cell_expands_to_valid_overrides(monkeypatch):
    for k, v in json.load(open(ROOT / "experiments" / "e2_params.json")).items():
        monkeypatch.setenv(k, v)
    exp = json.load(open(ROOT / "experiments" / "e2.json"))
    ids = [c["id"] for c in exp["cells"]]
    assert len(ids) == len(set(ids)) == 15 and "E2k-period-window" in ids
    for cell in exp["cells"]:
        rx.expand(cell["model"])
        for item in cell.get("set", []):
            path, _, value = rx.expand(item).partition("=")
            parsed = json.loads(value)
            if path == "chunking" and parsed["kind"] == "procedure":
                re.compile(parsed["heading_pattern"].replace("(?<", "(?<"))  # lookbehinds are fixed width
                re.compile(parsed["step_pattern"])
    k = next(c for c in exp["cells"] if c["id"] == "E2k-period-window")
    assert k["set"] == ["generation.num_ctx=2048"] and k["model"] == "$E2_MODEL"
