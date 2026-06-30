"""
Terraform validation service.

Runs `terraform init` + `terraform validate -json` inside an isolated
temporary directory (sandbox). Every run gets a fresh sandbox so LLM-generated
code is never written into the actual repository.

Security guarantees (§12.4):
  - Argument lists only — never shell=True, never string concatenation
  - A fixed, configured binary path from settings — not a bare "terraform"
  - An explicit, minimal env dict — don't inherit the full parent environment
  - Explicit timeouts on every subprocess call
  - Fresh tempdir per run, auto-deleted on exit

Performance optimisation (§12.2):
  - TF_PLUGIN_CACHE_DIR points to a persistent directory outside the sandbox
  - Avoids re-downloading the AWS provider (~300 MB) on every single run
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

from pydantic import BaseModel

from app.core.config import settings


# ── Result schema ─────────────────────────────────────────────────────────
class ValidationResult(BaseModel):
    """
    The output of a terraform validate run.

    valid:      True if `terraform validate -json` reported {"valid": true}
    raw_output: The full JSON string from validate's stdout, or the stderr
                from a failed `terraform init` / unexpected error.
    """

    valid: bool
    raw_output: str


def _ensure_plugin_cache_dir() -> None:
    """
    Create the plugin cache directory if it doesn't already exist.

    Called once before the first validation run. The directory is persistent
    across runs — that's the whole point — so subsequent `terraform init`
    calls reuse cached provider binaries instead of re-downloading them.
    """
    cache_dir = Path(settings.TERRAFORM_PLUGIN_CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)


def _build_subprocess_env() -> dict[str, str]:
    """
    Build a minimal, explicit environment dict for subprocess calls.

    Why not just inherit the full parent environment?
    - Principle of least privilege: the subprocess only needs PATH (to find
      system tools), the plugin cache dir, and the automation flag.
    - Prevents accidental leakage of secrets (GEMINI_API_KEY, DATABASE_URL)
      into Terraform's process space.
    """
    env: dict[str, str] = {
        "PATH": os.environ.get("PATH", ""),
        "TF_PLUGIN_CACHE_DIR": str(Path(settings.TERRAFORM_PLUGIN_CACHE_DIR).resolve()),
        "TF_IN_AUTOMATION": "1",
    }

    # Include essential OS variables for Windows & Unix/Linux runners (GitHub Actions CI)
    for var in (
        "SYSTEMROOT", "TEMP", "TMP", "HOMEDRIVE", "HOMEPATH", "USERPROFILE",
        "HOME", "TMPDIR", "SSL_CERT_FILE", "SSL_CERT_DIR", "XDG_CACHE_HOME",
        "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy"
    ):
        if var in os.environ:
            env[var] = os.environ[var]

    return env


async def validate_terraform(code: str) -> ValidationResult:
    """
    Validate a Terraform configuration string.

    Steps:
    1. Write the code to a fresh temporary directory as main.tf
    2. Run `terraform init -backend=false` to download/cache the provider
    3. Run `terraform validate -json` to check the code
    4. Parse the JSON output and return a ValidationResult
    5. The temp directory is auto-deleted (context manager)

    Args:
        code: The full contents of a Terraform file (main.tf) to validate.

    Returns:
        ValidationResult with valid=True/False and the raw JSON output.
    """
    # Ensure the persistent plugin cache exists before first run
    _ensure_plugin_cache_dir()

    terraform_binary = settings.TERRAFORM_BINARY_PATH
    env = _build_subprocess_env()

    with tempfile.TemporaryDirectory(prefix="heal-") as sandbox:
        # Write the code under test into the sandbox
        tf_file = Path(sandbox) / "main.tf"
        tf_file.write_text(code, encoding="utf-8")

        # ── Step 1: terraform init ────────────────────────────────────────
        # -backend=false  → don't try to configure a remote state backend
        # -input=false    → don't prompt for interactive input
        # -no-color       → strip ANSI escape codes from output
        try:
            init_result = subprocess.run(
                [terraform_binary, "init", "-backend=false", "-input=false", "-no-color"],
                cwd=sandbox,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError:
            return ValidationResult(
                valid=False,
                raw_output=f"Terraform binary not found at: {terraform_binary}",
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                valid=False,
                raw_output="terraform init timed out after 120 seconds",
            )

        if init_result.returncode != 0:
            return ValidationResult(
                valid=False,
                raw_output=f"terraform init failed:\n{init_result.stderr}",
            )

        # ── Step 2: terraform validate ────────────────────────────────────
        # -json     → machine-readable output (never regex-parse human text)
        # -no-color → clean output
        try:
            validate_result = subprocess.run(
                [terraform_binary, "validate", "-json", "-no-color"],
                cwd=sandbox,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return ValidationResult(
                valid=False,
                raw_output="terraform validate timed out after 30 seconds",
            )

        # ── Step 3: Parse the JSON output ─────────────────────────────────
        # terraform validate -json always outputs JSON to stdout, even on
        # validation failure — the exit code differs but stdout is JSON either way.
        try:
            parsed = json.loads(validate_result.stdout)
            return ValidationResult(
                valid=parsed["valid"],
                raw_output=validate_result.stdout,
            )
        except (json.JSONDecodeError, KeyError) as exc:
            # Shouldn't happen with a working Terraform binary, but handle
            # gracefully rather than crashing the healing pipeline.
            return ValidationResult(
                valid=False,
                raw_output=(
                    f"Failed to parse terraform validate output: {exc}\n"
                    f"stdout: {validate_result.stdout}\n"
                    f"stderr: {validate_result.stderr}"
                ),
            )
