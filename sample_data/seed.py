"""Create the demo job and upload the sample CVs through the real API.

    python sample_data/seed.py [--api http://localhost:8000]
"""
import argparse
from pathlib import Path

import httpx

from samples import JOB

CV_DIR = Path(__file__).parent / "cvs"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    api = ap.parse_args().api.rstrip("/")

    job = httpx.post(f"{api}/api/jobs", json=JOB, timeout=10).raise_for_status().json()
    print("created job", job["id"], job["title"])

    pdfs = sorted(CV_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit("No PDFs in sample_data/cvs — run generate_cvs.py first")
    files = [("files", (p.name, p.read_bytes(), "application/pdf")) for p in pdfs]
    res = httpx.post(f"{api}/api/jobs/{job['id']}/applications", files=files, timeout=60)
    print(res.status_code, res.json())
