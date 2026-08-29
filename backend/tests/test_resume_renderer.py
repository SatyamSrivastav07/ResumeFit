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
                    "github_link": "https://github.com/test-user/resumefit",
                    "live_link": "https://resumefit.example.com",
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


def test_obvious_technical_skills_and_tools_are_separated() -> None:
    resume = ResumeSchema.model_validate(
        {
            "skills": {
                "technical": ["Git", "CSS", "Docker"],
                "tools": ["CSS", "React", "Postman", "MongoDB"],
            }
        }
    )

    assert resume.skills.technical == ["CSS", "React", "MongoDB"]
    assert resume.skills.tools == ["Postman", "Git", "Docker"]


def test_render_html_hides_empty_sections_and_escapes_untrusted_content() -> None:
    resume = sample_resume()
    resume.summary = '<script>alert("x")</script>'
    resume.projects[0].link = "javascript:alert(1)"
    html = render_resume_html(resume)

    assert "&lt;script&gt;" in html
    assert '<script>alert("x")</script>' not in html
    assert 'href="javascript:' not in html
    assert 'href="https://github.com/test-user/resumefit"' in html
    assert 'href="https://resumefit.example.com"' in html
    assert ">GitHub<" in html
    assert ">Live Demo<" in html
    assert ">Achievements<" not in html
    assert ">Certifications<" not in html


def test_generate_pdf_is_valid_and_text_is_ats_readable() -> None:
    pdf_bytes = generate_resume_pdf(sample_resume())
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1_000

    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        assert document.page_count == 1
        extracted = "\n".join(page.get_text() for page in document)
        link_targets = {
            link.get("uri")
            for page in document
            for link in page.get_links()
            if link.get("uri")
        }

    assert "https://github.com/test-user" in link_targets
    assert "https://github.com/test-user/resumefit" in link_targets
    assert "https://resumefit.example.com" in link_targets

    for expected in (
        "Test User",
        "Skills",
        "Python",
        "Experience",
        "Software Intern",
        "Example Corp",
        "Projects",
        "ResumeFit AI",
        "GitHub",
        "Live Demo",
        "Education",
        "B.Tech",
        "Computer Science",
    ):
        assert expected.lower() in extracted.lower()


def test_dense_resume_is_compacted_to_exactly_one_page() -> None:
    data = sample_resume().model_dump()
    data["skills"]["technical"] = [f"Technical Skill {index}" for index in range(24)]
    data["skills"]["tools"] = [f"Tool Platform {index}" for index in range(36)]
    data["experience"][0]["description"] = [
        f"Built and maintained a reliable application workflow for business use case {index}."
        for index in range(4)
    ]
    data["projects"] = [
        {
            "name": f"Project {index}",
            "technologies": ["Python", "FastAPI", "React", "PostgreSQL"],
            "description": [
                "Built a full-stack application with secure APIs and maintainable workflows.",
                "Implemented authentication, persistence, testing, and deployment automation.",
            ],
        }
        for index in range(4)
    ]
    data["education"] = [
        {
            "institution": f"Education Institution {index}",
            "degree": "B.Tech",
            "field": "Computer Science and Engineering",
            "score": "CGPA: 8.0",
            "start_date": "2022",
            "end_date": "2026",
        }
        for index in range(3)
    ]
    data["achievements"] = [
        "Solved more than one thousand programming problems.",
        "Won a university-level engineering competition.",
        "Led a student sports team in inter-college competitions.",
    ]

    pdf_bytes = generate_resume_pdf(ResumeSchema.model_validate(data))

    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        assert document.page_count == 1
        extracted = document[0].get_text()
    assert "TECHNICAL SKILLS & TOOLS" in extracted
    assert "Tools & Platforms" in extracted
    assert "Project 3" in extracted
    assert "Education Institution 2" in extracted
