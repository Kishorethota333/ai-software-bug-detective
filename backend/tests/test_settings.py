import pytest
from pydantic import ValidationError

from app.config.settings import Settings


def test_non_development_requires_unique_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(
            _env_file=None,
            environment="production",
            jwt_secret="development-only-change-me",
        )


def test_production_cors_uses_only_configured_origins():
    settings = Settings(
        _env_file=None,
        environment="production",
        jwt_secret="a-unique-production-signing-secret-with-enough-entropy",
        cors_origins="https://app.example.com",
    )

    assert settings.cors_origin_list == ["https://app.example.com"]


def test_development_includes_local_frontend_origins():
    settings = Settings(_env_file=None, environment="development")

    assert "http://localhost:5173" in settings.cors_origin_list
    assert "http://127.0.0.1:5174" in settings.cors_origin_list
