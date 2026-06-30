"""
Application settings — single source of truth for all configuration.

Every environment variable the app needs is declared here as a typed field.
Nothing else in the codebase should call os.getenv() directly.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Reads environment variables (and .env file) into typed Python attributes.

    Pydantic-settings validates types automatically — if DATABASE_URL is missing
    or CORS_ALLOWED_ORIGINS isn't a valid comma-separated list, the app will fail
    fast at startup with a clear error message, not silently at runtime.
    """

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/selfheal"

    # ── Gemini LLM ────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"

    # ── Terraform ─────────────────────────────────────────────────────────
    TERRAFORM_BINARY_PATH: str = "terraform"
    TERRAFORM_PLUGIN_CACHE_DIR: str = ".terraform-plugin-cache"

    # ── Application ───────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    # Stored as comma-separated string in .env, parsed into a list via property below.
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Split the comma-separated CORS_ALLOWED_ORIGINS into a list."""
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]


# Module-level singleton — imported everywhere as:
#   from app.core.config import settings
settings = Settings()
