#!/usr/bin/env python3
"""List the PDF links on a web page, best matches for operation manuals first.

usage: manual_links.py <page-url> [max-links]
Prints one absolute URL per line. Fetch errors print nothing and exit 0.
"""
import re, sys, urllib.parse, urllib.request

url, cap = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 8
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
except Exception as e:
    print(f"# fetch failed: {e}", file=sys.stderr)
    sys.exit(0)
links = {urllib.parse.urljoin(url, m) for m in re.findall(r'href=["\']([^"\'#]+\.pdf[^"\']*)', html, re.I)}
score = lambda u: -sum(w in u.lower() for w in ("operat", "instruction", "manual", "maint", "iom", "omm"))
for u in sorted(links, key=lambda u: (score(u), u))[:cap]:
    print(u)
