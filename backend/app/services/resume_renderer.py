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


def project_links(project: Any) -> list[dict[str, str]]:
    """Return unique, safe project links while supporting older parsed records."""

    def field(name: str) -> Any:
        return project.get(name) if isinstance(project, dict) else getattr(project, name, None)

    candidates = [
        ("GitHub", field("github_link")),
        ("Live Demo", field("live_link")),
        ("Legacy", field("link")),
    ]
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for label, value in candidates:
        href = safe_web_url(value)
        if not href or href in seen:
            continue
        if label == "Legacy":
            label = "GitHub" if urlparse(href).netloc.casefold().endswith("github.com") else "Live Demo"
        seen.add(href)
        result.append({"label": label, "href": href})
    return result


def _environment() -> Environment:
    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(enabled_extensions=("html", "xml"), default_for_string=True),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.filters["safe_web_url"] = safe_web_url
    environment.globals["project_links"] = project_links
    return environment


def render_resume_html(resume: ResumeSchema, compact_level: int = 0) -> str:
    data = _sanitize_data(resume.model_dump())
    template = _environment().get_template("ats_resume.html")
    return template.render(resume=data, compact_level=compact_level)


def validate_pdf_bytes(pdf_bytes: bytes) -> None:
    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF-") or len(pdf_bytes) < MINIMUM_PDF_SIZE:
        raise ResumeRenderingError("PDF renderer returned invalid output.")


def _paragraph_text(value: Any) -> str:
    return escape(_meaningful_text(value), quote=True)


def _generate_reportlab_pdf(resume: ResumeSchema, compact_level: int = 0) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    density = min(max(compact_level, 0), 4)
    body_size = (8.8, 8.2, 7.7, 7.2, 6.7)[density]
    body_leading = (10.3, 9.5, 8.8, 8.1, 7.5)[density]
    section_gap = (5.2, 4.5, 3.8, 3.2, 2.7)[density]
    item_gap = (1.5, 1.2, 0.9, 0.6, 0.4)[density]
    margin = (11, 10, 9, 8, 7)[density] * mm

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title=_meaningful_text(resume.personal_info.name) or "Resume",
    )
    sample = getSampleStyleSheet()
    body = ParagraphStyle("ResumeBody", parent=sample["BodyText"], fontName="Times-Roman", fontSize=body_size, leading=body_leading, spaceAfter=0)
    centered = ParagraphStyle("ResumeContact", parent=body, alignment=TA_CENTER, spaceAfter=2)
    name_style = ParagraphStyle("ResumeName", parent=centered, fontName="Times-Bold", fontSize=17.5 - density * .6, leading=19.5 - density * .5, spaceAfter=1)
    heading = ParagraphStyle(
        "ResumeHeading",
        parent=body,
        fontName="Times-Bold",
        fontSize=10.5 - density * .25,
        leading=11.5 - density * .2,
        spaceBefore=section_gap,
        spaceAfter=1.5,
        borderWidth=0,
        borderPadding=0,
        keepWithNext=True,
        textTransform="uppercase",
    )
    item_heading = ParagraphStyle("ResumeItemHeading", parent=body, fontName="Times-Bold", fontSize=body_size + .45, leading=body_leading, keepWithNext=True, spaceBefore=item_gap)
    bullet_style = ParagraphStyle("ResumeBullet", parent=body, leftIndent=8, firstLineIndent=-6, bulletIndent=0, spaceAfter=item_gap)
    skill_label = ParagraphStyle("SkillLabel", parent=body, fontName="Times-Bold", textColor=colors.HexColor("#111111"))

    story: list[Any] = []

    def add_heading(title: str) -> None:
        heading_table = Table(
            [[Paragraph(_paragraph_text(title).upper(), heading)]],
            colWidths=[document.width],
            hAlign="LEFT",
        )
        heading_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), .8),
            ("LINEBELOW", (0, 0), (-1, -1), .55, colors.black),
        ]))
        story.append(heading_table)

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
        story.append(Paragraph(_paragraph_text(resume.summary), centered))

    if resume.education:
        add_heading("Education")
        for item in resume.education:
            dates = " - ".join(filter(None, (_meaningful_text(item.start_date), _meaningful_text(item.end_date))))
            title = _paragraph_text(item.institution)
            if dates:
                title += f" &nbsp;&nbsp; {_paragraph_text(dates)}"
            story.append(Paragraph(title, item_heading))
            course = " in ".join(filter(None, (_meaningful_text(item.degree), _meaningful_text(item.field))))
            details = " | ".join(filter(None, (course, _meaningful_text(item.location), _meaningful_text(item.score))))
            if details:
                story.append(Paragraph(_paragraph_text(details), body))

    skill_rows = (("Technical Skills", resume.skills.technical), ("Tools & Platforms", resume.skills.tools), ("Soft Skills", resume.skills.soft))
    populated_skill_rows = []
    for label, entries in skill_rows:
        cleaned = [_meaningful_text(entry) for entry in entries if _meaningful_text(entry)]
        if cleaned:
            populated_skill_rows.append([
                Paragraph(_paragraph_text(label), skill_label),
                Paragraph(", ".join(_paragraph_text(entry) for entry in cleaned), body),
            ])
    if populated_skill_rows:
        add_heading("Technical Skills & Tools")
        skills_table = Table(populated_skill_rows, colWidths=[27 * mm, None], hAlign="LEFT")
        skills_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), .8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), .8),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F1F1")),
            ("LINEBELOW", (0, 0), (-1, -2), .25, colors.HexColor("#C8C8C8")),
        ]))
        story.append(skills_table)

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
            title = _paragraph_text(item.name)
            links = project_links(item)
            if links:
                rendered_links = " | ".join(
                    f'<link href="{escape(link["href"], quote=True)}">{link["label"]}</link>'
                    for link in links
                )
                title += f" &nbsp;&nbsp; {rendered_links}"
            story.append(Paragraph(title, item_heading))
            if item.technologies:
                technologies = ", ".join(_paragraph_text(value) for value in item.technologies if _meaningful_text(value))
                if technologies:
                    story.append(Paragraph(f"<b>Tech:</b> {technologies}", body))
            add_bullets(item.description)

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


def _page_count(pdf_bytes: bytes) -> int:
    try:
        import fitz

        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            return document.page_count
    except Exception as exc:
        raise ResumeRenderingError("Unable to validate generated PDF pagination.") from exc


def generate_resume_pdf(resume: ResumeSchema) -> bytes:
    html_renderer = _load_weasy_html()
    pdf_bytes = b""
    for compact_level in range(5):
        try:
            if html_renderer is None:
                pdf_bytes = _generate_reportlab_pdf(resume, compact_level)
            else:
                html = render_resume_html(resume, compact_level)
                pdf_bytes = html_renderer(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()
        except Exception as exc:
            raise ResumeRenderingError("Unable to render the optimized resume PDF.") from exc
        validate_pdf_bytes(pdf_bytes)
        if _page_count(pdf_bytes) == 1:
            return pdf_bytes
    raise ResumeRenderingError(
        "Resume content is too long to fit legibly on one page. Reduce or reject some edits."
    )
