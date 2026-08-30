from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HUBGIT_", env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./hubgit.db"
    data_dir: Path = Path(".data")
    cookie_name: str = "hubgit_session"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_domain: str | None = None
    session_hours: int = Field(default=24, ge=1, le=24 * 30)
    max_request_bytes: int = Field(default=1_048_576, ge=1_024, le=10 * 1_048_576)
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    environment: Literal["development", "test", "production"] = "development"
    instance_name: str = "HubGit"
    public_base_url: str = "http://localhost:8000"
    branding: str = "hubgit"
    registration_enabled: bool = False
    mock_login: str = "demo"
    mock_password: str = "demo-password"
    seed_mock_user: bool = True

    @staticmethod
    def origin_from_url(value: str) -> str:
        parsed = urlsplit(value.strip())
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Origin must be an absolute HTTP(S) URL.")
        return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), "", "", ""))

    @staticmethod
    def _origin(value: str) -> str:
        parsed = urlsplit(value.strip())
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("Origins must not include a path, query, or fragment.")
        return Settings.origin_from_url(value)

    @property
    def public_origin(self) -> str:
        return self._origin(self.public_base_url)

    @property
    def cors_origin_list(self) -> list[str]:
        return [self._origin(value) for value in self.cors_origins.split(",") if value.strip()]

    @property
    def trusted_request_origins(self) -> set[str]:
        return {*self.cors_origin_list, self.public_origin}

    @model_validator(mode="after")
    def validate_security_configuration(self) -> "Settings":
        cookie_name_characters = set("!#$%&'*+-.^_|~0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        cookie_name_characters.add(chr(96))
        if not self.cookie_name or any(character not in cookie_name_characters for character in self.cookie_name):
            raise ValueError("Cookie name contains invalid characters.")
        if self.cookie_domain and (
            not self.cookie_domain.isascii()
            or any(not (character.isalnum() or character in ".-") for character in self.cookie_domain)
        ):
            raise ValueError("Cookie domain contains invalid characters.")

        origins = self.cors_origin_list
        if not origins:
            raise ValueError("At least one CORS origin is required.")
        if len(origins) != len(set(origins)):
            raise ValueError("CORS origins must be unique.")
        public_origin = self.public_origin

        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("SameSite=None cookies require the Secure attribute.")
        if self.environment == "production":
            if not self.cookie_secure:
                raise ValueError("Production requires secure session cookies.")
            if urlsplit(public_origin).scheme != "https":
                raise ValueError("Production requires an HTTPS public base URL.")
            if any(urlsplit(origin).scheme != "https" for origin in origins):
                raise ValueError("Production CORS origins must use HTTPS.")
            if self.seed_mock_user:
                raise ValueError("Production must not seed the mock user.")
        return self
