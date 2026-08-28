from app.schemas.job import JobAnalysisSchema
from app.schemas.resume import ResumeSchema
from app.services.resume_matcher import calculate_resume_match, normalize_skill


def make_resume(
    *,
    technical: list[str] | None = None,
    tools: list[str] | None = None,
    experience: bool = True,
    projects: bool = True,
    education: bool = True,
) -> ResumeSchema:
    return ResumeSchema.model_validate(
        {
            "personal_info": {
                "name": "Candidate",
                "email": "candidate@example.com",
                "location": "India",
            },
            "summary": "Backend engineer experienced in REST APIs, scalable systems, and CI/CD.",
            "skills": {
                "technical": technical or [],
                "tools": tools or [],
                "soft": ["Communication"],
            },
            "experience": [
                {
                    "company": "Example Corp",
                    "role": "Software Engineer",
                    "description": [
                        "Build and maintain backend services using Python, React, PostgreSQL, AWS, Docker, Git, and REST APIs.",
                        "Design scalable systems and CI/CD workflows while collaborating with engineering teams.",
                    ],
                }
            ] if experience else [],
            "projects": [
                {
                    "name": "Platform API",
                    "technologies": ["Python", "React", "PostgreSQL", "AWS", "Docker", "Git", "CI/CD", "REST APIs"],
                    "description": [
                        "Build and maintain backend services, design scalable systems, and create CI/CD workflows."
                    ],
                }
            ] if projects else [],
            "education": [
                {
                    "institution": "Example University",
                    "degree": "B.Tech",
                    "field": "Computer Science and Engineering",
                }
            ] if education else [],
        }
    )


def make_job(
    *,
    required: list[str] | None = None,
    preferred: list[str] | None = None,
    education_requirements: list[str] | None = None,
) -> JobAnalysisSchema:
    return JobAnalysisSchema.model_validate(
        {
            "company": "Example Corp",
            "role": "Software Engineer",
            "experience_level": "Entry Level",
            "employment_type": "Full-time",
            "required_skills": required if required is not None else ["Python", "React.js", "REST APIs", "PostgreSQL", "AWS"],
            "preferred_skills": preferred if preferred is not None else ["Docker"],
            "programming_languages": ["Python"],
            "frameworks": ["React"],
            "databases": ["PostgreSQL"],
            "cloud_and_devops": ["AWS", "Docker", "CI/CD"],
            "tools": ["Git"],
            "soft_skills": ["Communication"],
            "responsibilities": ["Build and maintain backend services", "Design scalable systems"],
            "education_requirements": education_requirements if education_requirements is not None else ["Bachelor's degree in Computer Science or related field"],
            "experience_requirements": ["0-2 years of software development experience"],
            "important_keywords": ["REST APIs", "scalable systems", "CI/CD"],
            "domain_keywords": ["backend"],
        }
    )


def test_perfect_match_scores_100() -> None:
    resume = make_resume(
        technical=["Python", "React", "REST APIs", "PostgreSQL", "Amazon Web Services"],
        tools=["Docker", "Git", "CI/CD"],
    )
    result = calculate_resume_match(resume, make_job())

    assert result.overall_score == 100
    assert result.breakdown.skills.score == 40
    assert result.missing_required_skills == []
    assert result.missing_preferred_skills == []


def test_no_matching_skills_scores_zero_for_skills() -> None:
    result = calculate_resume_match(
        make_resume(technical=["Ruby"], tools=["Rails"], experience=False, projects=False),
        make_job(required=["Python", "React"], preferred=["Docker"]),
    )
    assert result.breakdown.skills.score == 0
    assert result.missing_required_skills == ["Python", "React"]


def test_required_matches_but_preferred_missing_awards_required_portion() -> None:
    result = calculate_resume_match(
        make_resume(technical=["Python", "React"], tools=[]),
        make_job(required=["Python", "React"], preferred=["Kubernetes"]),
    )
    assert result.breakdown.skills.score == 30
    assert result.missing_preferred_skills == ["Kubernetes"]


def test_no_education_requirement_is_not_applicable_or_penalized() -> None:
    resume = make_resume(
        technical=["Python", "React", "REST APIs", "PostgreSQL", "AWS"],
        tools=["Docker", "Git", "CI/CD"],
        education=False,
    )
    result = calculate_resume_match(resume, make_job(education_requirements=[]))
    applicable = [
        category
        for category in result.breakdown.model_dump().values()
        if category["applicable"]
    ]
    expected = round(
        sum(category["score"] for category in applicable)
        / sum(category["max_score"] for category in applicable)
        * 100
    )

    assert result.breakdown.education.applicable is False
    assert result.overall_score == expected


def test_react_dot_js_matches_react() -> None:
    result = calculate_resume_match(
        make_resume(technical=["React"], experience=False, projects=False),
        make_job(required=["React.js"], preferred=[], education_requirements=[]),
    )
    assert result.breakdown.skills.score == 40


def test_nodejs_matches_node_dot_js() -> None:
    result = calculate_resume_match(
        make_resume(technical=["NodeJS"], experience=False, projects=False),
        make_job(required=["Node.js"], preferred=[], education_requirements=[]),
    )
    assert result.breakdown.skills.score == 40


def test_java_does_not_match_javascript() -> None:
    result = calculate_resume_match(
        make_resume(technical=["JavaScript"], experience=False, projects=False),
        make_job(required=["Java"], preferred=[], education_requirements=[]),
    )
    assert result.breakdown.skills.score == 0


def test_c_does_not_match_css() -> None:
    result = calculate_resume_match(
        make_resume(technical=["CSS"], experience=False, projects=False),
        make_job(required=["C"], preferred=[], education_requirements=[]),
    )
    assert result.breakdown.skills.score == 0


def test_aws_matches_amazon_web_services() -> None:
    result = calculate_resume_match(
        make_resume(technical=["Amazon Web Services"], experience=False, projects=False),
        make_job(required=["AWS"], preferred=[], education_requirements=[]),
    )
    assert result.breakdown.skills.score == 40


def test_empty_preferred_skills_redistributes_full_weight_to_required() -> None:
    result = calculate_resume_match(
        make_resume(technical=["Python"], experience=False, projects=False),
        make_job(required=["Python", "Docker"], preferred=[], education_requirements=[]),
    )
    assert result.breakdown.skills.score == 20


def test_normalization_is_deterministic_and_does_not_merge_react_native() -> None:
    assert normalize_skill(" React.JS ") == "react"
    assert normalize_skill("React Native") != normalize_skill("React")
    resume = make_resume(technical=["Python", "React"], experience=False, projects=False)
    job = make_job(required=["Python", "React"], preferred=[], education_requirements=[])
    assert calculate_resume_match(resume, job) == calculate_resume_match(resume, job)


def test_common_resume_and_jd_aliases_match() -> None:
    result = calculate_resume_match(
        make_resume(
            technical=[
                "HTML5",
                "CSS3",
                "Data Structures and Algorithms",
                "RAG",
                "MERN",
            ],
            experience=False,
            projects=False,
        ),
        make_job(
            required=[
                "HTML",
                "CSS",
                "Data Structures & Algorithms",
                "RAG systems",
                "MERN stack",
            ],
            preferred=[],
            education_requirements=[],
        ),
    )

    assert result.breakdown.skills.score == 40
    assert result.missing_required_skills == []
