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
    brand_preset: str = "hubgit"
    brand_name: str = "HubGit"
    brand_short_name: str = "HubGit"
    brand_logo_url: str | None = None
    brand_favicon_url: str | None = "/favicon.svg"
    brand_title_template: str = "%s · HubGit"
    brand_primary_color: str = "#0969da"
    brand_header_background: str = "#f6f8fa"
    brand_auth_heading: str = "Sign in to HubGit"
    brand_auth_explanation: str = "Provider-neutral Git collaboration for self-hosted teams."
    brand_connect_label: str = "Continue"
    brand_privacy_url: str | None = "/privacy"
    brand_terms_url: str | None = "/terms"
    brand_source_url: str | None = "https://github.com/not-the-ccp/hubgit-ui"
    brand_support_url: str | None = None
    brand_operator_notice: str | None = None
    brand_provider_label: str = "GitHub"
    provider: Literal["mock", "github"] = "mock"
    github_client_id: str | None = None
    github_client_secret_file: Path | None = None
    github_credential_key_file: Path | None = None
    github_web_base_url: str = "https://github.com"
    github_api_base_url: str = "https://api.github.com"
    github_callback_url: str | None = None
    github_access_policy_mode: Literal["any", "all"] = "any"
    github_allow_any_authorized_user: bool = True
    github_allowed_user_ids: str = ""
    github_required_organizations: str = ""
    github_required_teams: str = ""
    registration_enabled: bool = False
    mock_login: str = "demo"
    mock_password: str = "demo-password"
    seed_mock_user: bool = True

    @property
    def github_configured(self) -> bool:
        return bool(
            self.github_client_id
            and self.github_client_secret_file
            and self.github_credential_key_file
        )

    @property
    def github_redirect_uri(self) -> str:
        return self.github_callback_url or (
            f"{self.public_base_url.rstrip('/')}/api/v1/auth/providers/github/callback"
        )

    @staticmethod
    def _csv(value: str) -> tuple[str, ...]:
        return tuple(part.strip() for part in value.split(",") if part.strip())

    @property
    def github_access_policy(self) -> dict[str, object]:
        return {
            "mode": self.github_access_policy_mode,
            "allowAnyAuthorizedUser": self.github_allow_any_authorized_user,
            "userIds": tuple(int(value) for value in self._csv(self.github_allowed_user_ids)),
            "organizations": self._csv(self.github_required_organizations),
            "teams": self._csv(self.github_required_teams),
        }

    @property
    def branding_manifest(self) -> dict[str, object]:
        """Return the complete deployment branding boundary exposed to clients."""
        return {
            "preset": self.brand_preset,
            "productName": self.brand_name,
            "shortName": self.brand_short_name,
            "logoUrl": self.brand_logo_url,
            "faviconUrl": self.brand_favicon_url,
            "titleTemplate": self.brand_title_template,
            "colors": {
                "accent": self.brand_primary_color,
                "headerBackground": self.brand_header_background,
            },
            "authentication": {
                "heading": self.brand_auth_heading,
                "description": self.brand_auth_explanation,
                "connectLabel": self.brand_connect_label,
            },
            "links": {
                "privacy": self.brand_privacy_url,
                "terms": self.brand_terms_url,
                "source": self.brand_source_url,
                "support": self.brand_support_url,
            },
            "notice": self.brand_operator_notice,
            "providerDisplayNames": {
                "mock": "Local mock",
                "github": self.brand_provider_label,
            },
        }

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
            if self.provider == "github" and not self.github_configured:
                raise ValueError("Production GitHub deployments require client and encryption secrets.")

        try:
            tuple(int(value) for value in self._csv(self.github_allowed_user_ids))
        except ValueError as exc:
            raise ValueError("GitHub allowed user IDs must be comma-separated integers.") from exc
        if any("/" not in team or team.startswith("/") or team.endswith("/") for team in self._csv(self.github_required_teams)):
            raise ValueError("GitHub teams must use the organization/team-slug form.")
        for configured_url in (self.github_web_base_url, self.github_api_base_url, self.github_redirect_uri):
            parsed = urlsplit(configured_url)
            self.origin_from_url(configured_url)
            if parsed.query or parsed.fragment:
                raise ValueError("GitHub URLs must not include a query or fragment.")
            if self.environment == "production" and parsed.scheme != "https":
                raise ValueError("Production GitHub URLs must use HTTPS.")
        return self
