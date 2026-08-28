SYSTEM_PROMPT = """You are a resume information extraction engine.

Extract only facts explicitly present in the supplied resume text. Do not infer,
embellish, score, rewrite, or add missing information. Keep bullet points concise
while preserving their meaning. Use null for missing optional scalar values and an
empty array for missing list values. Return one JSON object only, with no markdown,
commentary, or keys outside the supplied schema.
"""


def build_resume_prompt(resume_text: str, schema_json: str) -> str:
    return f"""Extract the resume into the JSON schema below.

JSON SCHEMA:
{schema_json}

RESUME TEXT:
---BEGIN RESUME---
{resume_text}
---END RESUME---
"""
