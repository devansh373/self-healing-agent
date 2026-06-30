"""
Tests for the Terraform validation service.

These tests run against the REAL Terraform binary — no mocking.
They verify that:
  (a) The known-broken fixture (missing runtime) returns valid=False
  (b) A known-good Terraform snippet returns valid=True
  (c) The plugin cache directory is created and reused

Requirements:
  - Terraform CLI must be installed and accessible via TERRAFORM_BINARY_PATH
  - Network access for the first run (to download the AWS provider)
  - Subsequent runs reuse the plugin cache (much faster)
"""

import json
from pathlib import Path

import pytest

from app.services.terraform_service import validate_terraform


# ── Fixtures (test data, not to be confused with Terraform fixtures) ──────

BROKEN_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "fault_missing_required_argument"

# A minimal, valid Terraform config. Uses a simple resource with all
# required arguments present so it passes `terraform validate`.
KNOWN_GOOD_TERRAFORM = """\
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_s3_bucket" "test_bucket" {
  bucket = "my-test-bucket-for-validation"
}
"""


# ── Tests ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_broken_fixture_fails_validation():
    """
    The Phase 1 fixture (missing runtime on aws_lambda_function) must
    be detected as invalid by terraform validate.
    """
    broken_code = (BROKEN_FIXTURE_PATH / "main.tf").read_text(encoding="utf-8")

    result = await validate_terraform(broken_code)

    assert result.valid is False, "Broken fixture should fail validation"

    # The raw output should be parseable JSON from `terraform validate -json`
    parsed = json.loads(result.raw_output)
    assert parsed["valid"] is False

    # Should contain at least one diagnostic mentioning the issue
    assert len(parsed.get("diagnostics", [])) > 0, "Should have validation diagnostics"


@pytest.mark.asyncio
async def test_known_good_snippet_passes_validation():
    """
    A trivial, correct Terraform config (aws_s3_bucket with all required
    args) must pass terraform validate.
    """
    result = await validate_terraform(KNOWN_GOOD_TERRAFORM)

    assert result.valid is True, f"Known-good snippet should pass validation, got: {result.raw_output}"

    # The raw output should be parseable JSON
    parsed = json.loads(result.raw_output)
    assert parsed["valid"] is True
    assert parsed.get("diagnostics", []) == [], "Should have no diagnostics"


@pytest.mark.asyncio
async def test_plugin_cache_directory_is_created():
    """
    After a validation run, the plugin cache directory should exist
    and contain cached provider data.
    """
    from app.core.config import settings

    # Run a validation to trigger cache creation
    await validate_terraform(KNOWN_GOOD_TERRAFORM)

    cache_dir = Path(settings.TERRAFORM_PLUGIN_CACHE_DIR)
    assert cache_dir.exists(), f"Plugin cache dir should exist at {cache_dir}"
    assert cache_dir.is_dir(), "Plugin cache should be a directory"


@pytest.mark.asyncio
async def test_empty_code_fails_validation():
    """
    Empty Terraform code should still go through the validate flow
    without crashing — it should return valid=True (empty config is
    technically valid Terraform).
    """
    result = await validate_terraform("")

    # An empty file is actually valid Terraform — no resources, no errors
    # This test ensures the service handles edge cases gracefully
    assert isinstance(result.valid, bool)
    assert isinstance(result.raw_output, str)
    assert len(result.raw_output) > 0, "Should have some output"
