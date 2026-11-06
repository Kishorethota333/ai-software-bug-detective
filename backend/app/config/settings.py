
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Software Bug Detective"
    environment: str = "development"

    database_url: str = "sqlite:///./bug_detective.db"

    jwt_secret: str = "development-only-change-me"
    jwt_expire_minutes: int = Field(default=60, gt=0)

    cors_origins: str = ""

    upload_dir: str = "uploads"
    max_upload_mb: int = Field(default=10, gt=0)
    tesseract_cmd: str = ""

    ai_provider: str = "mock"
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    rag_embedding_api_url: str = ""
    rag_embedding_api_key: str = ""
    rag_embedding_model: str = "text-embedding-3-small"

    # Automated test runner configuration
    test_runner_timeout_seconds: int = 60
    test_runner_max_files: int = 200
    test_runner_max_output_chars: int = 20000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_deployment_settings(self) -> "Settings":
        if self.environment.strip().lower() not in {"development", "dev", "test"}:
            if (
                len(self.jwt_secret) < 32
                or "change-me" in self.jwt_secret.lower()
                or "replace-this" in self.jwt_secret.lower()
            ):
                raise ValueError(
                    "JWT_SECRET must be a unique, random value of at least 32 characters outside development."
                )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        configured_origins = [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]
        if self.environment.strip().lower() not in {"development", "dev", "test"}:
            return list(dict.fromkeys(configured_origins))
        required_local_origins = (
            "http://localhost:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
        )
        return list(dict.fromkeys([*configured_origins, *required_local_origins]))


settings = Settings()