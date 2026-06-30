"""
Integration tests for the deployments REST API endpoint and healing pipeline.

Verifies:
  - POST /api/deployments/trigger -> 201 with status="FAILED"
  - Background task triggers healing cycle
  - Mocks llm_service.generate_fix to return known-good HCL
  - Runs real terraform_service validation
  - GET /api/deployments/{id} eventually -> status="HEALED" with 1 attempt
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.services.llm_service import FixResult


KNOWN_GOOD_FIX_HCL = """terraform {
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

resource "aws_lambda_function" "healer_demo" {
  function_name = "self-healing-demo-fn"
  filename      = "function.zip"
  handler       = "index.handler"
  runtime       = "python3.12"
  role          = "arn:aws:iam::123456789012:role/lambda-role"
}
"""


@pytest.mark.asyncio
async def test_trigger_and_heal_deployment(client: AsyncClient):
    mock_fix = FixResult(
        explanation="Added required IAM role argument to aws_lambda_function resource.",
        fixed_code=KNOWN_GOOD_FIX_HCL,
    )

    with patch("app.services.llm_service.generate_fix", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_fix

        # 1. Trigger deployment
        response = await client.post("/api/deployments/trigger", json={})
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "FAILED"
        deployment_id = data["id"]

        # 2. Wait for background task to complete healing cycle
        final_status = None
        detail_data = {}
        for _ in range(30):
            await asyncio.sleep(0.5)
            detail_res = await client.get(f"/api/deployments/{deployment_id}")
            assert detail_res.status_code == 200
            detail_data = detail_res.json()
            if detail_data["status"] in ("HEALED", "FAILED_TO_HEAL"):
                final_status = detail_data["status"]
                break

        # 3. Assert final healed state
        assert final_status == "HEALED", f"Expected HEALED, got {final_status}. Log: {detail_data}"
        assert len(detail_data["attempts"]) == 1
        attempt = detail_data["attempts"][0]
        assert attempt["attempt_number"] == 1
        assert attempt["validation_success"] is True
        assert attempt["fixed_code"] == KNOWN_GOOD_FIX_HCL
