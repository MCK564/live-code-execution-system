from __future__ import annotations

from urllib.parse import urlparse

from pydantic.v1 import BaseSettings, Field, validator


def _validate_http_url(value: str, field_name: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be an absolute http(s) URL")
    return value


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str = Field(
        ...,
        env=["GOOGLE_REDIRECT_URI", "GOOGLE_REDIRECT_URIS"],
    )
    GOOGLE_AUTH_URI: str = Field(
        "https://accounts.google.com/o/oauth2/v2/auth",
        env="GOOGLE_AUTH_URI",
    )
    GOOGLE_TOKEN_URI: str = Field(
        "https://oauth2.googleapis.com/token",
        env="GOOGLE_TOKEN_URI",
    )
    GOOGLE_USERINFO_URI: str = Field(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        env="GOOGLE_USERINFO_URI",
    )

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_TTL_SECONDS: int
    JWT_REFRESH_TTL_SECONDS: int
    JWT_STATE_TTL_SECONDS: int

    AUTH_FRONTEND_SUCCESS_REDIRECT_URI: str = Field(
        "http://localhost:3000/login/success",
        env="AUTH_FRONTEND_SUCCESS_REDIRECT_URI",
    )
    AUTH_REDIRECT_ALLOWLIST: str = Field(
        "http://localhost:3000/login/success",
        env="AUTH_REDIRECT_ALLOWLIST",
    )
    AUTH_CODE_TTL_SECONDS: int = Field(60, env="AUTH_CODE_TTL_SECONDS")
    AUTH_USER_CACHE_TTL_SECONDS: int = Field(
        3600,
        env="AUTH_USER_CACHE_TTL_SECONDS",
    )
    BACKEND_CORS_ORIGINS: str = Field(
        "http://localhost:3000,http://localhost:5173",
        env="BACKEND_CORS_ORIGINS",
    )
    AUTH_REFRESH_COOKIE_NAME: str = Field(
        "refresh_token",
        env="AUTH_REFRESH_COOKIE_NAME",
    )
    AUTH_COOKIE_SECURE: bool = Field(True, env="AUTH_COOKIE_SECURE")
    AUTH_COOKIE_SAMESITE: str = Field("lax", env="AUTH_COOKIE_SAMESITE")
    AUTH_COOKIE_DOMAIN: str | None = Field(None, env="AUTH_COOKIE_DOMAIN")
    AUTH_COOKIE_PATH: str = Field("/", env="AUTH_COOKIE_PATH")
    AUTH_ISSUER: str = Field(
        "live-code-execution-system",
        env="AUTH_ISSUER",
    )

    class Config:
        env_file = ".env"

    @validator(
        "GOOGLE_REDIRECT_URI",
        "GOOGLE_AUTH_URI",
        "GOOGLE_TOKEN_URI",
        "GOOGLE_USERINFO_URI",
        "AUTH_FRONTEND_SUCCESS_REDIRECT_URI",
    )
    def validate_urls(cls, value: str, field):  # noqa: N805
        return _validate_http_url(value, field.name)

    @validator("AUTH_REDIRECT_ALLOWLIST")
    def validate_redirect_allowlist(cls, value: str):  # noqa: N805
        items = [item.strip() for item in value.split(",") if item.strip()]
        if not items:
            raise ValueError("AUTH_REDIRECT_ALLOWLIST must contain at least one URL")

        for item in items:
            _validate_http_url(item, "AUTH_REDIRECT_ALLOWLIST")
        return ",".join(items)

    @validator("BACKEND_CORS_ORIGINS")
    def validate_backend_cors_origins(cls, value: str):  # noqa: N805
        items = [item.strip() for item in value.split(",") if item.strip()]
        if not items:
            raise ValueError("BACKEND_CORS_ORIGINS must contain at least one URL")

        for item in items:
            _validate_http_url(item, "BACKEND_CORS_ORIGINS")
        return ",".join(items)

    @validator("AUTH_COOKIE_SAMESITE")
    def validate_cookie_samesite(cls, value: str):  # noqa: N805
        normalized = value.lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("AUTH_COOKIE_SAMESITE must be one of: lax, strict, none")
        return normalized

    @property
    def auth_redirect_allowlist(self) -> set[str]:
        return {
            item.strip()
            for item in self.AUTH_REDIRECT_ALLOWLIST.split(",")
            if item.strip()
        }

    @property
    def backend_cors_origins(self) -> list[str]:
        return [
            item.strip()
            for item in self.BACKEND_CORS_ORIGINS.split(",")
            if item.strip()
        ]


settings = Settings()
