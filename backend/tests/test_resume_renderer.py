import fitz

from app.schemas.resume import ResumeSchema
from app.services.resume_renderer import generate_resume_pdf, render_resume_html


def sample_resume() -> ResumeSchema:
    return ResumeSchema.model_validate(
        {
            "personal_info": {
                "name": "Test User",
                "email": "test@example.com",
                "github": "https://github.com/test-user",
            },
            "summary": "Backend engineer building reliable applications.",
            "skills": {"technical": ["Python", "React"]},
            "experience": [
                {
                    "company": "Example Corp",
                    "role": "Software Intern",
                    "description": ["Built API workflows using Python."],
                }
            ],
            "projects": [
                {
                    "name": "ResumeFit AI",
                    "description": ["Built an ATS resume tailoring workflow."],
                    "technologies": ["React", "FastAPI"],
                }
            ],
            "education": [
                {
                    "institution": "Example University",
                    "degree": "B.Tech",
                    "field": "Computer Science",
                }
            ],
        }
    )


def test_render_html_hides_empty_sections_and_escapes_untrusted_content() -> None:
    resume = sample_resume()
    resume.summary = '<script>alert("x")</script>'
    resume.projects[0].link = "javascript:alert(1)"
    html = render_resume_html(resume)

    assert "&lt;script&gt;" in html
    assert '<script>alert("x")</script>' not in html
    assert 'href="javascript:' not in html
    assert ">Achievements<" not in html
    assert ">Certifications<" not in html


def test_generate_pdf_is_valid_and_text_is_ats_readable() -> None:
    pdf_bytes = generate_resume_pdf(sample_resume())
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1_000

    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        extracted = "\n".join(page.get_text() for page in document)

    for expected in (
        "Test User",
        "Skills",
        "Python",
        "Experience",
        "Software Intern",
        "Example Corp",
        "Projects",
        "ResumeFit AI",
        "Education",
        "B.Tech",
        "Computer Science",
    ):
        assert expected.lower() in extracted.lower()
