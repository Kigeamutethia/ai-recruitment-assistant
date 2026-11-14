"""Render the fictional CVs in samples.py to PDFs in sample_data/cvs/.

    python sample_data/generate_cvs.py
"""
from pathlib import Path

import pymupdf

from samples import CVS

OUT = Path(__file__).parent / "cvs"


def render(text: str, path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page()  # A4-ish default
    rect = pymupdf.Rect(50, 50, page.rect.width - 50, page.rect.height - 50)
    page.insert_textbox(rect, text, fontsize=10, fontname="helv")
    doc.save(path)
    doc.close()


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, text in CVS.items():
        render(text, OUT / name)
        print("wrote", OUT / name)
