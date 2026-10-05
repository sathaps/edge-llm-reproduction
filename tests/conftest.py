import sys, threading
from pathlib import Path

import pytest
from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "pipelines" / "a_python"), str(ROOT / "tools"), str(ROOT / "scoring"), str(ROOT / "scripts")]

from stub_ollama import Stub  # noqa: E402

PAGES = [
    "Section 1. Starting the unit. Before starting, check the oil level. Check that the fuel valve is open. "
    "Step 1. Close the main breaker. Step 2. Set the selector to RUN. Step 3. Press START and hold for five seconds.",
    "Step 4. Release the START button. Step 5. Confirm that oil pressure rises above the minimum. "
    "Limits table. Oil pressure minimum 20 psi. Coolant temperature maximum 210 F. The load test applies to model X only. "
    "Model Y does not support the load test.",
    "Section 2. Stopping the unit. Remove the load. Run the unit for three minutes. Set the selector to OFF.",
    "Section 3. Storage. Drain the fuel for storage longer than ninety days. Disconnect the battery.",
]


@pytest.fixture
def pdf_path(tmp_path):
    pdf = FPDF()
    pdf.set_font("Helvetica", size=11)
    for text in PAGES:
        pdf.add_page()
        pdf.multi_cell(0, 6, text)
    p = tmp_path / "manual.pdf"
    pdf.output(str(p))
    return p


@pytest.fixture
def stub():
    s = Stub(("127.0.0.1", 0))
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    yield s
    s.shutdown()
    s.server_close()


@pytest.fixture
def url(stub):
    return f"http://127.0.0.1:{stub.server_address[1]}"
