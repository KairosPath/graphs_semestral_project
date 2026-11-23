"""Build the report PDF: insert the SPARQL queries from queries/*.rq into the
HTML template and print it to PDF with headless Chrome.

Usage (from semestral/): python report/build_report.py
"""
import html
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "report" / "report_template.html"
HTML_OUT = ROOT / "report" / "report.html"
PDF_OUT = ROOT / "report" / "MovieLens_Knowledge_Graph_Report.pdf"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def query_block(name):
    lines = (ROOT / "queries" / f"{name}.rq").read_text(encoding="utf-8").splitlines()
    body = [l for l in lines if not l.startswith("#") and not l.startswith("PREFIX")]
    while body and not body[0].strip():
        body.pop(0)
    return "<pre>" + html.escape("\n".join(body).rstrip()) + "</pre>"


page = TEMPLATE.read_text(encoding="utf-8")
page = re.sub(r"\{\{q:([a-z0-9_]+)\}\}", lambda m: query_block(m.group(1)), page)
HTML_OUT.write_text(page, encoding="utf-8")

with tempfile.TemporaryDirectory() as profile:
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
                    f"--user-data-dir={profile}", "--virtual-time-budget=8000",
                    "--no-pdf-header-footer", f"--print-to-pdf={PDF_OUT}",
                    HTML_OUT.as_uri()], check=True, capture_output=True)
print("written", PDF_OUT)
