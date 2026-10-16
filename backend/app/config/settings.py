
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Software Bug Detective"
    environment: str = "development"

    database_url: str = "sqlite:///./bug_detective.db"

    jwt_secret: str = "development-only-change-me"
    jwt_expire_minutes: int = 60

    cors_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    )

    upload_dir: str = "uploads"
    max_upload_mb: int = 10

    ai_provider: str = "mock"
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"

    # Automated test runner configuration
    test_runner_timeout_seconds: int = 60
    test_runner_max_files: int = 200
    test_runner_max_output_chars: int = 20000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


settings = Settings()