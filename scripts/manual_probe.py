#!/usr/bin/env python3
"""Download one manual, record its provenance and extract text per page.

usage: manual_probe.py <out-dir> <url>
A failed download is recorded in provenance.json and is not an error exit, so the
workflow can go on to the next candidate.
"""
import datetime, hashlib, json, os, re, subprocess, sys

out, url = sys.argv[1], sys.argv[2]
os.makedirs(f"{out}/pages", exist_ok=True)
pdf = f"{out}/manual.pdf"
prov = {"date_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "source_url": url}

r = subprocess.run(["curl", "-sS", "-L", "--retry", "2", "-m", "240", "-o", pdf, "-w",
                    "%{http_code} %{content_type} %{size_download}", url], capture_output=True, text=True)
prov["curl"] = (r.stdout or "").strip()
prov["curl_stderr"] = r.stderr.strip()[:300]
head = open(pdf, "rb").read(5) if os.path.exists(pdf) else b""
prov["is_pdf"] = prov["curl"].startswith("200") and head == b"%PDF-"
if not prov["is_pdf"]:
    json.dump(prov, open(f"{out}/provenance.json", "w"), indent=1)
    print(json.dumps(prov, indent=1)); sys.exit(0)

prov["sha256"] = hashlib.sha256(open(pdf, "rb").read()).hexdigest()
prov["size_bytes"] = os.path.getsize(pdf)
info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
m = re.search(r"^Pages:\s+(\d+)", info, re.M)
n = int(m.group(1)) if m else 0
prov["pages"] = n
prov["pdfinfo"] = {k.strip(): v.strip() for k, v in (l.split(":", 1) for l in info.splitlines() if ":" in l)}
texts = []
for p in range(1, n + 1):
    t = subprocess.run(["pdftotext", "-layout", "-f", str(p), "-l", str(p), pdf, "-"], capture_output=True, text=True).stdout
    open(f"{out}/pages/{p:03d}.txt", "w").write(t)
    texts.append(t)
chars = [len(t.strip()) for t in texts]
prov["pages_with_under_200_chars"] = sum(1 for c in chars if c < 200)
prov["total_chars"] = sum(chars)
json.dump(prov, open(f"{out}/provenance.json", "w"), indent=1)
print(json.dumps({k: v for k, v in prov.items() if k != "pdfinfo"}, indent=1))
print("Title/Producer:", prov["pdfinfo"].get("Title"), "|", prov["pdfinfo"].get("Producer"), "|", prov["pdfinfo"].get("CreationDate"))

with open(f"{out}/cover.txt", "w") as f:
    for p in range(min(4, n)):
        f.write(f"===== PDF page {p+1} =====\n{texts[p]}\n")

lic = re.compile(r"distribution statement|approved for public release|distribution is unlimited|copyright|©|all rights reserved|"
                 r"may not be (copied|reproduced)|reproduc|redistribut|proprietary|confidential", re.I)
with open(f"{out}/licence.txt", "w") as f:
    for p in list(range(min(6, n))) + list(range(max(6, n - 3), n)):
        for line in texts[p].splitlines():
            if lic.search(line):
                f.write(f"[pdf p{p+1}] {line.strip()}\n")
print("===== licence / distribution lines =====")
print(open(f"{out}/licence.txt").read()[:2500])

pat = re.compile(r"(applies?\s+(only\s+)?to|applicable\s+(only\s+)?to|not\s+applicable|does\s+not\s+apply|do\s+not\s+apply|"
                 r"only\s+(on|for|with|to)\s+(the\s+)?(model|models|spec|unit|units|series|size|sizes)|"
                 r"(models?|spec|series|sizes?)\s+[A-Za-z0-9\-/ ,]{1,30}\s+only|"
                 r"except\s+(for\s+)?(the\s+)?(model|models|spec|series|size)|excluding|"
                 r"not\s+(available|used|installed|present|supplied|included|equipped|required)\s+(on|with|in|for)|"
                 r"if\s+equipped|where\s+equipped|\bN/A\b|"
                 r"(prior\s+to|before|after|starting\s+with|beginning\s+with)\s+(serial|spec|model))", re.I)
hits = 0
with open(f"{out}/applicability.txt", "w") as f:
    for p, t in enumerate(texts, 1):
        lines = t.splitlines()
        for i, line in enumerate(lines):
            if pat.search(line):
                hits += 1
                ctx = " | ".join(x.strip() for x in lines[max(0, i-1):i+2] if x.strip())
                f.write(f"[pdf p{p}] {ctx}\n")
print(f"===== applicability matches: {hits} =====")
print(open(f"{out}/applicability.txt").read()[:9000])
