import json
import logging
from functools import lru_cache

from mistralai.client import Mistral
from pydantic import ValidationError

from app.config import settings
from app.prompts.job_analyzer import SYSTEM_PROMPT as JOB_SYSTEM_PROMPT
from app.prompts.job_analyzer import build_job_analysis_prompt
from app.prompts.resume_parser import SYSTEM_PROMPT, build_resume_prompt
from app.schemas.job import JobAnalysisSchema
from app.schemas.resume import ResumeSchema

logger = logging.getLogger(__name__)


class MistralConfigurationError(RuntimeError):
    """Raised when Mistral is not configured."""


class MistralServiceError(RuntimeError):
    """Raised when Mistral cannot complete the request."""


class MistralResponseError(MistralServiceError):
    """Raised when Mistral returns JSON that does not match the requested schema."""


@lru_cache(maxsize=1)
def get_mistral_client() -> Mistral:
    if not settings.mistral_api_key:
        raise MistralConfigurationError("MISTRAL_API_KEY is not configured.")
    return Mistral(api_key=settings.mistral_api_key)


def _message_content(response: object) -> str:
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise MistralResponseError("Mistral returned an empty response.") from exc
    if not isinstance(content, str) or not content.strip():
        raise MistralResponseError("Mistral returned an empty response.")
    return content


def parse_resume_text(resume_text: str) -> ResumeSchema:
    """Use Mistral JSON mode, then enforce the local Pydantic schema."""

    schema_json = json.dumps(ResumeSchema.model_json_schema(), ensure_ascii=False)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_resume_prompt(resume_text, schema_json)},
    ]
    client = get_mistral_client()

    for attempt in range(2):
        try:
            response = client.chat.complete(
                model=settings.mistral_model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0,
            )
        except Exception as exc:
            logger.warning("Mistral resume parsing request failed: %s", type(exc).__name__)
            raise MistralServiceError("Mistral request failed.") from exc

        try:
            payload = json.loads(_message_content(response))
            return ResumeSchema.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, MistralResponseError, TypeError):
            if attempt == 1:
                break
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your prior response was invalid. Return a complete JSON object "
                        "that exactly matches the supplied schema. Return JSON only."
                    ),
                }
            )

    raise MistralResponseError("Mistral returned invalid structured resume data.")


def analyze_job_description(
    company: str,
    role: str,
    job_description: str,
) -> JobAnalysisSchema:
    """Extract independently validated requirements from an untrusted job posting."""

    schema_json = json.dumps(JobAnalysisSchema.model_json_schema(), ensure_ascii=False)
    messages = [
        {"role": "system", "content": JOB_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_job_analysis_prompt(
                company=company,
                role=role,
                job_description=job_description,
                schema_json=schema_json,
            ),
        },
    ]
    client = get_mistral_client()

    for attempt in range(2):
        try:
            response = client.chat.complete(
                model=settings.mistral_model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0,
            )
        except Exception as exc:
            logger.warning("Mistral job analysis request failed: %s", type(exc).__name__)
            raise MistralServiceError("Mistral request failed.") from exc

        try:
            payload = json.loads(_message_content(response))
            if not isinstance(payload, dict):
                raise TypeError("Expected a JSON object.")
            payload["company"] = company
            payload["role"] = role
            return JobAnalysisSchema.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, MistralResponseError, TypeError):
            if attempt == 1:
                break
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Return valid JSON only matching the required JobAnalysisSchema. "
                        "Do not include markdown or explanatory text."
                    ),
                }
            )

    raise MistralResponseError("Mistral returned invalid structured job data.")
