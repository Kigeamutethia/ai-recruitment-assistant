"""PDF text extraction with PyMuPDF (imported as `pymupdf`)."""
import pymupdf

MIN_TEXT_CHARS = 100  # below this we assume a scanned/image-only PDF


class PdfExtractionError(Exception):
    pass


def extract_text(path: str) -> str:
    """Return the plain text of every page, in reading order."""
    try:
        with pymupdf.open(path) as doc:
            # sort=True orders text blocks top-to-bottom, left-to-right — helps two-column CVs.
            text = "\n".join(page.get_text("text", sort=True) for page in doc)
    except Exception as e:  # corrupt / encrypted files
        raise PdfExtractionError(f"Could not read PDF: {e}") from e
    if len(text.strip()) < MIN_TEXT_CHARS:
        raise PdfExtractionError("No extractable text — the PDF is probably scanned (OCR not supported yet)")
    return text


def looks_like_pdf(data: bytes) -> bool:
    return data[:5] == b"%PDF-"
