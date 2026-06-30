"""
LLM service — Gemini SDK integration for generating Terraform fixes.

Owns all interaction with the Google Gemini API. Exposes exactly one
public function: `generate_fix(broken_code, error_log) -> FixResult`.

Design decisions:
  - Uses the ASYNC client (`client.aio.models.generate_content`) so the
    event loop isn't blocked while waiting for the LLM response.
  - Uses Gemini's structured output (response_mime_type="application/json"
    + response_schema) to get predictable, parseable responses.
  - Does NOT handle exceptions internally — §11.4 says the caller
    (healing_service.py) wraps this in try/except so it can record
    the error in the healing_attempts table.
  - The prompt template, model name, and API key all come from a single
    source of truth (Settings), never hardcoded.
"""

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.core.config import settings


# ── Structured output schema ─────────────────────────────────────────────
# Gemini returns JSON conforming to this schema. Pydantic validates it
# on our side, giving us typed Python objects instead of raw dicts.
class FixResult(BaseModel):
    """
    The LLM's response to a fix request.

    explanation: 1-3 sentence description of what was wrong and what was changed.
    fixed_code:  The FULL corrected Terraform file (not a diff/patch).
    """

    explanation: str
    fixed_code: str


# ── Prompt template ───────────────────────────────────────────────────────
# The prompt instructs the model to:
# 1. Act as an SRE specialising in Terraform
# 2. Identify the bug from the code + error log
# 3. Explain it briefly (1-3 sentences)
# 4. Return the FULL corrected file (not just the changed lines)
# 5. Preserve everything that isn't the bug
#
# The {broken_code} and {error_log} placeholders are filled at call time.
PROMPT_TEMPLATE = """\
You are an expert Site Reliability Engineer specializing in Terraform/HCL.
You will be given a broken Terraform configuration file and the error log from a failed
deployment pipeline. Identify the bug, explain it in 1-3 sentences, and return the FULL
corrected file. Preserve every existing block (provider, required_providers, all resource
arguments that are not the bug) — change only what is needed to fix the reported error.

BROKEN FILE:
{broken_code}

ERROR LOG:
{error_log}
"""


# ── Gemini client ────────────────────────────────────────────────────────
# Created at module level so it's reused across requests (connection pooling).
# The API key comes from settings, which reads it from .env.
_client = genai.Client(api_key=settings.GEMINI_API_KEY)


async def generate_fix(broken_code: str, error_log: str) -> FixResult:
    """
    Ask Gemini to diagnose and fix a broken Terraform configuration.

    Args:
        broken_code: The full contents of the broken main.tf file.
        error_log:   The deployment pipeline error log (human-readable context).

    Returns:
        FixResult with the model's explanation and the full corrected file.

    Raises:
        Any exception from the Gemini SDK (network errors, quota errors,
        malformed responses) — the caller (healing_service) handles these.
    """
    prompt = PROMPT_TEMPLATE.format(broken_code=broken_code, error_log=error_log)

    response = await _client.aio.models.generate_content(
        model=settings.GEMINI_MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FixResult,
        ),
    )

    # response.text contains the JSON string conforming to FixResult's schema.
    # model_validate_json parses and validates it in one step.
    return FixResult.model_validate_json(response.text)
