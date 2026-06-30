"""
Throwaway smoke-test script for the LLM service.

Run this ONCE manually to verify the prompt/schema actually works
against the real Gemini API before wiring it into the orchestrator.

Usage:
    cd backend
    .venv\Scripts\python.exe scripts\smoke_test_llm.py

Prerequisites:
    - A real GEMINI_API_KEY in backend/.env
    - The virtual environment activated or called directly

This script is NOT part of the test suite — it makes a real API call
and requires a real API key. It exists only as a one-time verification
tool per §22 step 6.
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to Python path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.llm_service import generate_fix


# The same fixture used in the real pipeline
FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "fault_missing_required_argument"


async def main():
    # Check API key is set
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("your-"):
        print("ERROR: Set a real GEMINI_API_KEY in backend/.env first")
        print(f"Current value: {settings.GEMINI_API_KEY[:20]}...")
        sys.exit(1)

    print(f"Using model: {settings.GEMINI_MODEL_NAME}")
    print(f"API key: {settings.GEMINI_API_KEY[:8]}...{settings.GEMINI_API_KEY[-4:]}")
    print()

    # Load the fixture
    broken_code = (FIXTURE_DIR / "main.tf").read_text(encoding="utf-8")
    error_log = (FIXTURE_DIR / "error_log.txt").read_text(encoding="utf-8")

    print("=== BROKEN CODE ===")
    print(broken_code)
    print("=== ERROR LOG ===")
    print(error_log)
    print("=== CALLING GEMINI ===")

    try:
        result = await generate_fix(broken_code, error_log)
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}")
        sys.exit(1)

    print()
    print("=== LLM EXPLANATION ===")
    print(result.explanation)
    print()
    print("=== FIXED CODE ===")
    print(result.fixed_code)
    print()
    print("=== RESULT TYPE ===")
    print(f"Type: {type(result).__name__}")
    print(f"explanation length: {len(result.explanation)} chars")
    print(f"fixed_code length: {len(result.fixed_code)} chars")
    print(f"Contains 'role': {'role' in result.fixed_code}")
    print()
    print("SUCCESS — LLM service is working correctly!")


if __name__ == "__main__":
    asyncio.run(main())
