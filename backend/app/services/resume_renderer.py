from pathlib import Path
import ctypes
from html import escape
from io import BytesIO, StringIO
from contextlib import redirect_stderr, redirect_stdout
from functools import lru_cache
from typing import Any
import sys
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas.resume import ResumeSchema


class ResumeRenderingError(RuntimeError):
    """Raised when a valid ATS PDF cannot be rendered."""


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
MINIMUM_PDF_SIZE = 1_000


def _meaningful_text(value: Any) -> str:
    if value is None:
        return ""
    cleaned = str(value).strip()
    if cleaned.lower() in {"none", "null", "n/a", "na"}:
        return ""
    return cleaned


def _sanitize_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [cleaned for item in value if (cleaned := _sanitize_data(item)) not in (None, "", [], {})]
    if isinstance(value, str) or value is None:
        return _meaningful_text(value)
    return value


def safe_web_url(value: Any) -> str:
    cleaned = _meaningful_text(value)
    if not cleaned:
        return ""
    parsed = urlparse(cleaned)
    return cleaned if parsed.scheme.lower() in {"http", "https"} and parsed.netloc else ""


def _environment() -> Environment:
    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(enabled_extensions=("html", "xml"), default_for_string=True),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.filters["safe_web_url"] = safe_web_url
    return environment


def render_resume_html(resume: ResumeSchema) -> str:
    data = _sanitize_data(resume.model_dump())
    template = _environment().get_template("ats_resume.html")
    return template.render(resume=data)


def validate_pdf_bytes(pdf_bytes: bytes) -> None:
    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF-") or len(pdf_bytes) < MINIMUM_PDF_SIZE:
        raise ResumeRenderingError("PDF renderer returned invalid output.")


def _paragraph_text(value: Any) -> str:
    return escape(_meaningful_text(value), quote=True)


def _generate_reportlab_pdf(resume: ResumeSchema) -> bytes:
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=13 * mm,
        bottomMargin=13 * mm,
        title=_meaningful_text(resume.personal_info.name) or "Resume",
    )
    sample = getSampleStyleSheet()
    body = ParagraphStyle("ResumeBody", parent=sample["BodyText"], fontName="Helvetica", fontSize=9.5, leading=12)
    centered = ParagraphStyle("ResumeContact", parent=body, alignment=TA_CENTER, spaceAfter=2)
    name_style = ParagraphStyle("ResumeName", parent=centered, fontName="Helvetica-Bold", fontSize=20, leading=23, spaceAfter=3)
    heading = ParagraphStyle(
        "ResumeHeading",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=14,
        spaceBefore=8,
        spaceAfter=4,
        borderWidth=0,
        borderPadding=0,
        keepWithNext=True,
        textTransform="uppercase",
    )
    item_heading = ParagraphStyle("ResumeItemHeading", parent=body, fontName="Helvetica-Bold", fontSize=10, leading=12, keepWithNext=True)
    bullet_style = ParagraphStyle("ResumeBullet", parent=body, leftIndent=10, firstLineIndent=-7, spaceAfter=2)

    story: list[Any] = []

    def add_heading(title: str) -> None:
        story.append(Paragraph(_paragraph_text(title).upper(), heading))
        story.append(Spacer(1, 0.5 * mm))

    def add_bullets(entries: list[str]) -> None:
        for entry in entries:
            if _meaningful_text(entry):
                story.append(Paragraph(f"- {_paragraph_text(entry)}", bullet_style))

    info = resume.personal_info
    if _meaningful_text(info.name):
        story.append(Paragraph(_paragraph_text(info.name).upper(), name_style))
    contacts = [_meaningful_text(value) for value in (info.email, info.phone, info.location) if _meaningful_text(value)]
    if contacts:
        story.append(Paragraph(" | ".join(_paragraph_text(value) for value in contacts), centered))
    link_parts = []
    for label, value in (("LinkedIn", info.linkedin), ("GitHub", info.github), ("Portfolio", info.portfolio)):
        href = safe_web_url(value)
        if href:
            link_parts.append(f'<link href="{escape(href, quote=True)}">{label}</link>')
        elif _meaningful_text(value):
            link_parts.append(_paragraph_text(value))
    if link_parts:
        story.append(Paragraph(" | ".join(link_parts), centered))

    if _meaningful_text(resume.summary):
        add_heading("Summary")
        story.append(Paragraph(_paragraph_text(resume.summary), body))

    skill_rows = (("Technical", resume.skills.technical), ("Tools", resume.skills.tools), ("Soft Skills", resume.skills.soft))
    if any(entries for _, entries in skill_rows):
        add_heading("Skills")
        for label, entries in skill_rows:
            cleaned = [_meaningful_text(entry) for entry in entries if _meaningful_text(entry)]
            if cleaned:
                story.append(Paragraph(f"<b>{label}:</b> {', '.join(_paragraph_text(entry) for entry in cleaned)}", body))

    if resume.experience:
        add_heading("Experience")
        for item in resume.experience:
            dates = " - ".join(filter(None, (_meaningful_text(item.start_date), _meaningful_text(item.end_date))))
            title = f"{_paragraph_text(item.role)} - {_paragraph_text(item.company)}"
            if dates:
                title += f" &nbsp;&nbsp; {_paragraph_text(dates)}"
            story.append(Paragraph(title, item_heading))
            if _meaningful_text(item.location):
                story.append(Paragraph(_paragraph_text(item.location), body))
            add_bullets(item.description)

    if resume.projects:
        add_heading("Projects")
        for item in resume.projects:
            href = safe_web_url(item.link)
            title = _paragraph_text(item.name)
            if href:
                title += f' &nbsp;&nbsp; <link href="{escape(href, quote=True)}">Project Link</link>'
            story.append(Paragraph(title, item_heading))
            if item.technologies:
                technologies = ", ".join(_paragraph_text(value) for value in item.technologies if _meaningful_text(value))
                if technologies:
                    story.append(Paragraph(f"<b>Technologies:</b> {technologies}", body))
            add_bullets(item.description)

    if resume.education:
        add_heading("Education")
        for item in resume.education:
            dates = " - ".join(filter(None, (_meaningful_text(item.start_date), _meaningful_text(item.end_date))))
            title = _paragraph_text(item.institution)
            if dates:
                title += f" &nbsp;&nbsp; {_paragraph_text(dates)}"
            story.append(Paragraph(title, item_heading))
            course = ", ".join(filter(None, (_meaningful_text(item.degree), _meaningful_text(item.field))))
            details = " | ".join(filter(None, (course, _meaningful_text(item.location), _meaningful_text(item.score))))
            if details:
                story.append(Paragraph(_paragraph_text(details), body))

    for title, entries in (("Achievements", resume.achievements), ("Certifications", resume.certifications), ("Languages", resume.languages)):
        cleaned = [_meaningful_text(entry) for entry in entries if _meaningful_text(entry)]
        if cleaned:
            add_heading(title)
            add_bullets(cleaned)

    document.build(story)
    return output.getvalue()


@lru_cache(maxsize=1)
def _load_weasy_html() -> type | None:
    if sys.platform == "win32":
        try:
            ctypes.CDLL("libgobject-2.0-0.dll")
        except OSError:
            return None
    try:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            from weasyprint import HTML

        return HTML
    except Exception:
        return None


def generate_resume_pdf(resume: ResumeSchema) -> bytes:
    html = render_resume_html(resume)
    html_renderer = _load_weasy_html()
    if html_renderer is None:
        try:
            pdf_bytes = _generate_reportlab_pdf(resume)
        except Exception as exc:
            raise ResumeRenderingError("Unable to render the optimized resume PDF.") from exc
    else:
        try:
            pdf_bytes = html_renderer(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()
        except Exception as exc:
            raise ResumeRenderingError("Unable to render the optimized resume PDF.") from exc
    validate_pdf_bytes(pdf_bytes)
    return pdf_bytes
