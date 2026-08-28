import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from app.schemas.job import JobAnalysisSchema
from app.schemas.match import CategoryScore, MatchAnalysisSchema, MatchBreakdown
from app.schemas.resume import EducationItem, ResumeSchema

SKILLS_WEIGHT = 40.0
EXPERIENCE_WEIGHT = 25.0
PROJECTS_WEIGHT = 15.0
KEYWORDS_WEIGHT = 10.0
EDUCATION_WEIGHT = 5.0
COMPLETENESS_WEIGHT = 5.0

REQUIRED_SKILLS_POINTS = 30.0
PREFERRED_SKILLS_POINTS = 10.0

SKILL_ALIASES = {
    "reactjs": "react",
    "nodejs": "nodejs",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "js": "javascript",
    "javascript": "javascript",
    "amazonwebservices": "aws",
    "aws": "aws",
    "cicd": "cicd",
    "restapi": "restapi",
    "restapis": "restapi",
    "restfulapi": "restapi",
    "restfulapis": "restapi",
    "html5": "html",
    "html": "html",
    "css3": "css",
    "css": "css",
    "datastructuresalgorithms": "dsa",
    "datastructuresandalgorithms": "dsa",
    "dsa": "dsa",
    "retrievalaugmentedgeneration": "rag",
    "ragsystem": "rag",
    "ragsystems": "rag",
    "rag": "rag",
    "mernstack": "mern",
    "mern": "mern",
}

PHRASE_ALIASES = {
    "react": [("react",), ("reactjs",), ("react", "js")],
    "nodejs": [("nodejs",), ("node", "js")],
    "postgresql": [("postgresql",), ("postgres",)],
    "javascript": [("javascript",), ("js",)],
    "aws": [("aws",), ("amazon", "web", "services")],
    "cicd": [("cicd",), ("ci", "cd")],
    "restapi": [("restapi",), ("restapis",), ("rest", "api"), ("rest", "apis")],
    "html": [("html",), ("html5",)],
    "css": [("css",), ("css3",)],
    "dsa": [
        ("dsa",),
        ("data", "structures", "algorithms"),
        ("data", "structures", "and", "algorithms"),
    ],
    "rag": [
        ("rag",),
        ("rag", "system"),
        ("rag", "systems"),
        ("retrieval", "augmented", "generation"),
    ],
    "mern": [("mern",), ("mern", "stack")],
}

ROLE_STOPWORDS = {"and", "the", "of", "for", "a", "an"}
EDUCATION_DEGREES = {
    "bachelor": {"bachelor", "bachelors", "btech", "be"},
    "master": {"master", "masters", "mtech", "me", "msc"},
    "doctorate": {"phd", "doctorate", "doctoral"},
}


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        normalized = normalize_skill(cleaned)
        if cleaned and normalized and normalized not in seen:
            seen.add(normalized)
            result.append(cleaned)
    return result


def normalize_skill(value: str) -> str:
    compact = re.sub(r"[^a-z0-9]+", "", value.casefold())
    return SKILL_ALIASES.get(compact, compact)


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.casefold())


def _contains_sequence(tokens: list[str], sequence: tuple[str, ...], canonical: str) -> bool:
    width = len(sequence)
    for index in range(len(tokens) - width + 1):
        if tuple(tokens[index : index + width]) != sequence:
            continue
        if canonical == "react" and width == 1:
            if index + 1 < len(tokens) and tokens[index + 1] == "native":
                continue
        return True
    return False


def phrase_in_text(phrase: str, text: str) -> bool:
    canonical = normalize_skill(phrase)
    text_tokens = _tokens(text)
    phrase_tokens = tuple(_tokens(phrase))
    sequences = list(PHRASE_ALIASES.get(canonical, []))
    if phrase_tokens and phrase_tokens not in sequences:
        sequences.append(phrase_tokens)
    return any(_contains_sequence(text_tokens, sequence, canonical) for sequence in sequences)


def collect_resume_skills(resume: ResumeSchema) -> dict[str, str]:
    explicit = [
        *resume.skills.technical,
        *resume.skills.tools,
        *resume.skills.soft,
        *(technology for project in resume.projects for technology in project.technologies),
    ]
    collected: dict[str, str] = {}
    for skill in explicit:
        normalized = normalize_skill(skill)
        if normalized and normalized not in collected:
            collected[normalized] = skill.strip()
    return collected


def _job_technology_terms(job: JobAnalysisSchema) -> list[str]:
    return _unique(
        [
            *job.required_skills,
            *job.preferred_skills,
            *job.programming_languages,
            *job.frameworks,
            *job.databases,
            *job.cloud_and_devops,
            *job.tools,
        ]
    )


def calculate_skill_score(
    resume: ResumeSchema,
    job: JobAnalysisSchema,
) -> tuple[CategoryScore, list[str], list[str], list[str]]:
    resume_skills = collect_resume_skills(resume)
    required = _unique(job.required_skills)
    preferred = _unique(job.preferred_skills)

    matched_required = [item for item in required if normalize_skill(item) in resume_skills]
    matched_preferred = [item for item in preferred if normalize_skill(item) in resume_skills]
    missing_required = [item for item in required if normalize_skill(item) not in resume_skills]
    missing_preferred = [item for item in preferred if normalize_skill(item) not in resume_skills]

    if required and preferred:
        score = REQUIRED_SKILLS_POINTS * len(matched_required) / len(required)
        score += PREFERRED_SKILLS_POINTS * len(matched_preferred) / len(preferred)
    elif required:
        score = SKILLS_WEIGHT * len(matched_required) / len(required)
    elif preferred:
        score = SKILLS_WEIGHT * len(matched_preferred) / len(preferred)
    else:
        score = 0.0

    matched = _unique([*matched_required, *matched_preferred])
    return (
        CategoryScore(
            score=round(score, 2),
            max_score=SKILLS_WEIGHT,
            applicable=bool(required or preferred),
        ),
        matched,
        missing_required,
        missing_preferred,
    )


def _coverage(terms: list[str], text: str) -> tuple[float, list[str]]:
    if not terms:
        return 0.0, []
    matched = [term for term in terms if phrase_in_text(term, text)]
    return len(matched) / len(terms), matched


def _experience_label(role: str, company: str) -> str:
    return f"{role} — {company}" if company else role


def calculate_experience_score(
    resume: ResumeSchema,
    job: JobAnalysisSchema,
) -> tuple[CategoryScore, list[str], list[str]]:
    technology_terms = _job_technology_terms(job)
    responsibility_terms = _unique([*job.responsibilities, *job.important_keywords])
    domain_terms = _unique(job.domain_keywords)
    combined_text = "\n".join(
        f"{item.role}\n" + "\n".join(item.description) for item in resume.experience
    )

    score = 5.0 if resume.experience else 0.0
    technology_coverage, _ = _coverage(technology_terms, combined_text)
    responsibility_coverage, _ = _coverage(responsibility_terms, combined_text)
    score += 10.0 * technology_coverage
    score += 5.0 * responsibility_coverage

    job_role_tokens = set(_tokens(job.role)) - ROLE_STOPWORDS
    role_or_domain_match = False
    relevant: list[str] = []
    for item in resume.experience:
        item_text = f"{item.role}\n" + "\n".join(item.description)
        role_overlap = bool(job_role_tokens & set(_tokens(item.role)))
        domain_overlap = any(phrase_in_text(term, item_text) for term in domain_terms)
        technology_overlap = any(phrase_in_text(term, item_text) for term in technology_terms)
        responsibility_overlap = any(
            phrase_in_text(term, item_text) for term in responsibility_terms
        )
        if role_overlap or domain_overlap:
            role_or_domain_match = True
        if role_overlap or domain_overlap or technology_overlap or responsibility_overlap:
            relevant.append(_experience_label(item.role, item.company))

    if role_or_domain_match:
        score += 5.0

    strengths: list[str] = []
    if relevant:
        strengths.append(f"{len(relevant)} experience item(s) contain relevant role, skill, or responsibility terms.")
    return (
        CategoryScore(score=round(min(score, EXPERIENCE_WEIGHT), 2), max_score=EXPERIENCE_WEIGHT, applicable=True),
        relevant,
        strengths,
    )


def calculate_project_score(
    resume: ResumeSchema,
    job: JobAnalysisSchema,
) -> tuple[CategoryScore, list[str], list[str]]:
    technology_terms = _job_technology_terms(job)
    context_terms = _unique([*job.responsibilities, *job.important_keywords])
    applicable = bool(technology_terms or context_terms)
    if not applicable:
        return CategoryScore(score=0, max_score=PROJECTS_WEIGHT, applicable=False), [], []

    project_technologies = {
        normalize_skill(value)
        for project in resume.projects
        for value in project.technologies
        if normalize_skill(value)
    }
    matched_technologies = [
        term for term in technology_terms if normalize_skill(term) in project_technologies
    ]
    technology_score = (
        8.0 * len(matched_technologies) / len(technology_terms)
        if technology_terms
        else 0.0
    )
    combined_project_text = "\n".join(
        f"{project.name}\n"
        + "\n".join(project.technologies)
        + "\n"
        + "\n".join(project.description)
        for project in resume.projects
    )
    context_coverage, _ = _coverage(context_terms, combined_project_text)
    score = (2.0 if resume.projects else 0.0) + technology_score + 5.0 * context_coverage

    relevant: list[str] = []
    for project in resume.projects:
        explicit_matches = [
            term
            for term in technology_terms
            if normalize_skill(term)
            in {normalize_skill(value) for value in project.technologies}
        ]
        project_text = (
            f"{project.name}\n"
            + "\n".join(project.technologies)
            + "\n"
            + "\n".join(project.description)
        )
        context_match = any(phrase_in_text(term, project_text) for term in context_terms)
        if explicit_matches or context_match:
            suffix = f" — {', '.join(_unique(explicit_matches))}" if explicit_matches else ""
            relevant.append(f"{project.name}{suffix}")

    strengths: list[str] = []
    if relevant:
        strengths.append(f"{len(relevant)} project(s) contain relevant technologies or job terminology.")
    return (
        CategoryScore(score=round(min(score, PROJECTS_WEIGHT), 2), max_score=PROJECTS_WEIGHT, applicable=True),
        relevant,
        strengths,
    )


def _professional_resume_text(resume: ResumeSchema) -> str:
    parts = [resume.summary or ""]
    parts.extend(resume.skills.technical)
    parts.extend(resume.skills.tools)
    parts.extend(resume.skills.soft)
    for item in resume.experience:
        parts.append(item.role)
        parts.extend(item.description)
    for project in resume.projects:
        parts.append(project.name)
        parts.extend(project.technologies)
        parts.extend(project.description)
    return "\n".join(parts)


def calculate_keyword_score(
    resume: ResumeSchema,
    job: JobAnalysisSchema,
) -> tuple[CategoryScore, list[str], list[str]]:
    keywords = _unique(job.important_keywords)
    if not keywords:
        return CategoryScore(score=0, max_score=KEYWORDS_WEIGHT, applicable=False), [], []
    resume_text = _professional_resume_text(resume)
    matched = [keyword for keyword in keywords if phrase_in_text(keyword, resume_text)]
    missing = [keyword for keyword in keywords if not phrase_in_text(keyword, resume_text)]
    score = KEYWORDS_WEIGHT * len(matched) / len(keywords)
    return (
        CategoryScore(score=round(score, 2), max_score=KEYWORDS_WEIGHT, applicable=True),
        matched,
        missing,
    )


def _degree_level(text: str) -> str | None:
    tokens = set(_tokens(text))
    compact_text = normalize_skill(text)
    for canonical, aliases in EDUCATION_DEGREES.items():
        for alias in aliases:
            if alias in tokens:
                return canonical
            if len(alias) >= 3 and alias in compact_text:
                return canonical
    return None


def _computer_science_present(text: str) -> bool:
    compact = normalize_skill(text)
    return any(term in compact for term in ("computerscience", "cse", "computerscienceandengineering"))


def _education_relevance(requirement: str, education: list[EducationItem]) -> float:
    resume_text = "\n".join(
        " ".join(
            value
            for value in (item.institution, item.degree, item.field)
            if value
        )
        for item in education
    )
    if not resume_text:
        return 0.0

    required_degree = _degree_level(requirement)
    resume_degree = _degree_level(resume_text)
    requires_cs = _computer_science_present(requirement)
    resume_has_cs = _computer_science_present(resume_text)

    signals: list[bool] = []
    if required_degree:
        signals.append(required_degree == resume_degree)
    if requires_cs:
        signals.append(resume_has_cs)
    if signals:
        return sum(signals) / len(signals)

    requirement_tokens = set(_tokens(requirement)) - {
        "degree", "in", "or", "a", "an", "the", "related", "field", "equivalent"
    }
    resume_tokens = set(_tokens(resume_text))
    return 1.0 if requirement_tokens and requirement_tokens & resume_tokens else 0.0


def calculate_education_score(
    resume: ResumeSchema,
    job: JobAnalysisSchema,
) -> CategoryScore:
    requirements = _unique(job.education_requirements)
    if not requirements:
        return CategoryScore(score=0, max_score=EDUCATION_WEIGHT, applicable=False)
    relevance = sum(
        _education_relevance(requirement, resume.education) for requirement in requirements
    ) / len(requirements)
    return CategoryScore(
        score=round(EDUCATION_WEIGHT * relevance, 2),
        max_score=EDUCATION_WEIGHT,
        applicable=True,
    )


def calculate_completeness_score(resume: ResumeSchema) -> CategoryScore:
    info = resume.personal_info
    contact_present = any(
        value for value in (info.email, info.phone, info.location, info.linkedin, info.github, info.portfolio)
    )
    skills_present = bool(collect_resume_skills(resume))
    work_present = bool(resume.experience or resume.projects)
    education_present = bool(resume.education)
    bullet_content = [
        bullet
        for item in resume.experience
        for bullet in item.description
    ] + [bullet for project in resume.projects for bullet in project.description]
    meaningful_bullets = any(len(bullet.strip()) >= 20 for bullet in bullet_content)
    score = sum(
        [contact_present, skills_present, work_present, education_present, meaningful_bullets]
    )
    return CategoryScore(score=float(score), max_score=COMPLETENESS_WEIGHT, applicable=True)


def _rounded_overall(breakdown: MatchBreakdown) -> int:
    categories = [
        breakdown.skills,
        breakdown.experience,
        breakdown.projects,
        breakdown.keywords,
        breakdown.education,
        breakdown.completeness,
    ]
    earned = sum(category.score for category in categories if category.applicable)
    available = sum(category.max_score for category in categories if category.applicable)
    if available == 0:
        return 0
    normalized = Decimal(str(earned * 100 / available))
    return int(normalized.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_resume_match(
    resume: ResumeSchema,
    job: JobAnalysisSchema,
) -> MatchAnalysisSchema:
    skill_score, matched_skills, missing_required, missing_preferred = calculate_skill_score(resume, job)
    experience_score, relevant_experience, experience_strengths = calculate_experience_score(resume, job)
    project_score, relevant_projects, project_strengths = calculate_project_score(resume, job)
    keyword_score, matched_keywords, missing_keywords = calculate_keyword_score(resume, job)
    education_score = calculate_education_score(resume, job)
    completeness_score = calculate_completeness_score(resume)

    breakdown = MatchBreakdown(
        skills=skill_score,
        experience=experience_score,
        projects=project_score,
        keywords=keyword_score,
        education=education_score,
        completeness=completeness_score,
    )

    strengths: list[str] = []
    if job.required_skills:
        matched_required_count = len(job.required_skills) - len(missing_required)
        strengths.append(
            f"Matches {matched_required_count} of {len(job.required_skills)} required skills listed by the job."
        )
    strengths.extend(experience_strengths)
    strengths.extend(project_strengths)
    if matched_keywords:
        strengths.append(f"{len(matched_keywords)} important job keyword(s) are represented in the resume.")
    if education_score.applicable and education_score.score > 0:
        strengths.append("The resume contains education relevant to the stated requirement.")

    gaps = [
        f"{skill} was not found in the uploaded resume, although the job lists it as required."
        for skill in missing_required
    ]
    gaps.extend(
        f"{skill} is listed as preferred but was not found in the uploaded resume."
        for skill in missing_preferred
    )
    gaps.extend(
        f"{keyword} terminology from the job was not represented in the uploaded resume."
        for keyword in missing_keywords
    )
    if education_score.applicable and education_score.score == 0:
        gaps.append("Education matching the stated job requirement was not found in the uploaded resume.")

    return MatchAnalysisSchema(
        overall_score=_rounded_overall(breakdown),
        breakdown=breakdown,
        matched_skills=matched_skills,
        missing_required_skills=missing_required,
        missing_preferred_skills=missing_preferred,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        relevant_experience=relevant_experience,
        relevant_projects=relevant_projects,
        strengths=strengths,
        gaps=gaps,
    )
