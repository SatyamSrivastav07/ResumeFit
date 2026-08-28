import re

import fitz

MIN_VISIBLE_CHARACTERS = 50
MAX_TEXT_CHARACTERS = 50_000


class PDFParseError(ValueError):
    """Raised when PDF bytes cannot be opened or read."""


class UnreadablePDFError(PDFParseError):
    """Raised for protected PDFs or PDFs without useful selectable text."""


class ResumeTextTooLongError(PDFParseError):
    """Raised when extracted text exceeds the parser safety limit."""


def _clean_page_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        cleaned = re.sub(r"[\t ]+", " ", line).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract selectable text in page order from in-memory PDF bytes."""

    if not pdf_bytes:
        raise PDFParseError("The PDF is empty or corrupt.")

    document = None
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        if document.needs_pass:
            raise UnreadablePDFError("Password-protected PDFs are not supported.")

        pages = [_clean_page_text(page.get_text("text")) for page in document]
        extracted = "\n\n".join(page for page in pages if page).strip()
    except (UnreadablePDFError, ResumeTextTooLongError):
        raise
    except (fitz.FileDataError, RuntimeError, ValueError) as exc:
        raise PDFParseError("The PDF is corrupt or unreadable.") from exc
    finally:
        if document is not None:
            document.close()

    visible_characters = len(re.sub(r"\s+", "", extracted))
    if visible_characters < MIN_VISIBLE_CHARACTERS:
        raise UnreadablePDFError(
            "The PDF does not contain enough selectable text. Scanned PDFs are not supported yet."
        )
    if len(extracted) > MAX_TEXT_CHARACTERS:
        raise ResumeTextTooLongError("The extracted resume text is too long to parse.")

    return extracted
