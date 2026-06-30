"""
Tests for the LLM service.

Mocks the google-genai client entirely — no real network call, no real
API key needed in CI. Verifies:
  1. The prompt includes both broken_code and error_log
  2. A fabricated structured response is correctly parsed into a FixResult
  3. The correct model name from settings is used
  4. The async client path (client.aio.models) is used, not the sync one
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm_service import FixResult, PROMPT_TEMPLATE, generate_fix


# ── Test data ─────────────────────────────────────────────────────────────

SAMPLE_BROKEN_CODE = """\
resource "aws_lambda_function" "demo" {
  function_name = "demo-fn"
  filename      = "function.zip"
  handler       = "index.handler"
  runtime       = "python3.12"
}
"""

SAMPLE_ERROR_LOG = """\
[2026-06-19T10:00:04Z] ERROR The argument "role" is required, but no definition was found.
"""

# This is what the mocked LLM "returns" — a valid FixResult as JSON
MOCK_LLM_RESPONSE_JSON = (
    '{"explanation": "The aws_lambda_function resource was missing the required '
    '\\"role\\" argument. Added the IAM execution role ARN.", '
    '"fixed_code": "resource \\"aws_lambda_function\\" \\"demo\\" {\\n'
    '  function_name = \\"demo-fn\\"\\n'
    '  role          = \\"arn:aws:iam::123456789012:role/lambda-role\\"\\n'
    '  filename      = \\"function.zip\\"\\n'
    '  handler       = \\"index.handler\\"\\n'
    '  runtime       = \\"python3.12\\"\\n'
    '}"}'
)


# ── Tests ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_fix_parses_response_correctly():
    """
    Given a mocked LLM response, verify that generate_fix returns
    a properly parsed FixResult with the expected fields.
    """
    # Build a mock that simulates: client.aio.models.generate_content(...)
    # The response object has a .text property returning our fake JSON.
    mock_response = MagicMock()
    mock_response.text = MOCK_LLM_RESPONSE_JSON

    mock_generate = AsyncMock(return_value=mock_response)

    with patch("app.services.llm_service._client") as mock_client:
        mock_client.aio.models.generate_content = mock_generate

        result = await generate_fix(SAMPLE_BROKEN_CODE, SAMPLE_ERROR_LOG)

    # Verify the result is a FixResult with correct data
    assert isinstance(result, FixResult)
    assert "role" in result.explanation.lower()
    assert "role" in result.fixed_code
    assert "aws_lambda_function" in result.fixed_code


@pytest.mark.asyncio
async def test_prompt_includes_broken_code_and_error_log():
    """
    Verify that the actual prompt sent to the LLM contains both the
    broken code and the error log — the model needs both for context.
    """
    mock_response = MagicMock()
    mock_response.text = MOCK_LLM_RESPONSE_JSON

    mock_generate = AsyncMock(return_value=mock_response)

    with patch("app.services.llm_service._client") as mock_client:
        mock_client.aio.models.generate_content = mock_generate

        await generate_fix(SAMPLE_BROKEN_CODE, SAMPLE_ERROR_LOG)

    # Extract the actual prompt that was passed to generate_content
    call_args = mock_generate.call_args
    actual_prompt = call_args.kwargs.get("contents") or call_args.args[0]

    # The prompt must contain both inputs
    assert SAMPLE_BROKEN_CODE.strip() in actual_prompt, (
        "Prompt must include the broken code"
    )
    assert SAMPLE_ERROR_LOG.strip() in actual_prompt, (
        "Prompt must include the error log"
    )


@pytest.mark.asyncio
async def test_correct_model_name_is_used():
    """
    Verify that the model name from settings is passed to the SDK,
    not a hardcoded value.
    """
    from app.core.config import settings

    mock_response = MagicMock()
    mock_response.text = MOCK_LLM_RESPONSE_JSON

    mock_generate = AsyncMock(return_value=mock_response)

    with patch("app.services.llm_service._client") as mock_client:
        mock_client.aio.models.generate_content = mock_generate

        await generate_fix(SAMPLE_BROKEN_CODE, SAMPLE_ERROR_LOG)

    call_args = mock_generate.call_args
    actual_model = call_args.kwargs.get("model")

    assert actual_model == settings.GEMINI_MODEL_NAME, (
        f"Should use model from settings ({settings.GEMINI_MODEL_NAME}), "
        f"got: {actual_model}"
    )


@pytest.mark.asyncio
async def test_structured_output_config_is_set():
    """
    Verify that the request configures structured JSON output with
    the FixResult schema — this is what makes the LLM return parseable
    JSON instead of freeform text.
    """
    mock_response = MagicMock()
    mock_response.text = MOCK_LLM_RESPONSE_JSON

    mock_generate = AsyncMock(return_value=mock_response)

    with patch("app.services.llm_service._client") as mock_client:
        mock_client.aio.models.generate_content = mock_generate

        await generate_fix(SAMPLE_BROKEN_CODE, SAMPLE_ERROR_LOG)

    call_args = mock_generate.call_args
    config = call_args.kwargs.get("config")

    assert config is not None, "Should pass a GenerateContentConfig"
    assert config.response_mime_type == "application/json", (
        "Should request JSON output"
    )
    assert config.response_schema == FixResult, (
        "Should use FixResult as the response schema"
    )


def test_prompt_template_has_required_placeholders():
    """
    Sanity check: the prompt template string must contain {broken_code}
    and {error_log} placeholders.
    """
    assert "{broken_code}" in PROMPT_TEMPLATE
    assert "{error_log}" in PROMPT_TEMPLATE


def test_fix_result_schema_has_required_fields():
    """
    Verify the FixResult Pydantic model has the expected fields
    with the correct types.
    """
    fields = FixResult.model_fields

    assert "explanation" in fields, "FixResult must have 'explanation' field"
    assert "fixed_code" in fields, "FixResult must have 'fixed_code' field"

    # Verify they're string types
    assert fields["explanation"].annotation is str
    assert fields["fixed_code"].annotation is str
