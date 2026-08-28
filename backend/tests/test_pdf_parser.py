import fitz
import pytest

from app.services.pdf_parser import PDFParseError, UnreadablePDFError, extract_text_from_pdf


def _pdf_bytes(*page_texts: str) -> bytes:
    document = fitz.open()
    for text in page_texts:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    result = document.tobytes()
    document.close()
    return result


def test_extracts_text_from_pages_in_order() -> None:
    text = extract_text_from_pdf(
        _pdf_bytes(
            "Satyam Srivastav\nSoftware Engineer with Python and FastAPI experience.",
            "EXPERIENCE\nBuilt reliable APIs and automated resume workflows.",
        )
    )

    assert "Satyam Srivastav" in text
    assert text.index("Satyam Srivastav") < text.index("EXPERIENCE")


def test_corrupt_pdf_is_rejected() -> None:
    with pytest.raises(PDFParseError):
        extract_text_from_pdf(b"%PDF-this-is-not-a-real-document")


def test_textless_pdf_is_rejected() -> None:
    with pytest.raises(UnreadablePDFError, match="selectable text"):
        extract_text_from_pdf(_pdf_bytes(""))
