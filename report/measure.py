"""Export the report to PDF with Word, then store the page number (body numbering starts at 1 on the first page after the contents) of every contents entry."""
import json, re, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
import os
DOC = Path(os.environ["REPORT_OUT"]) if os.environ.get("REPORT_OUT") else HERE.parent / "4th Year_UEMK_AI&ML_PROJECT REPORT FORMAT (2).docx"
PDF = HERE / "out" / "report.pdf"
PDF.parent.mkdir(exist_ok=True)
r = subprocess.run(["powershell", "-NoProfile", "-File", str(HERE / "measure.ps1"), "-Doc", str(DOC), "-Pdf", str(PDF)], capture_output=True, text=True)
print(r.stdout.strip(), r.stderr.strip()[:300])
import fitz
pdf = fitz.open(PDF)
norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()
texts = [norm(p.get_text()) for p in pdf]
toc = json.loads((HERE / "toc.json").read_text(encoding="utf8"))
pages, last = {}, 4
for e in toc:
    key = norm(e["text"])[:60]
    found = next((i for i in range(max(last, 4), len(pdf)) if key in texts[i]), None)
    if found is None:
        print("NOT FOUND:", e["text"]); continue
    pages[e["bookmark"]] = found - 3   # pdf page 5 is body page 1
    last = found
(HERE / "pages.json").write_text(json.dumps(pages), encoding="utf8")
print("pdf pages:", len(pdf), "| body pages:", len(pdf) - 4, "| headings located:", len(pages), "of", len(toc))
