from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HUBGIT_", env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./hubgit.db"
    data_dir: Path = Path(".data")
    cookie_name: str = "hubgit_session"
    cookie_secure: bool = False
    session_hours: int = 24
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    instance_name: str = "HubGit"
    public_base_url: str = "http://localhost:8000"
    branding: str = "hubgit"
    registration_enabled: bool = False
    mock_login: str = "demo"
    mock_password: str = "demo-password"

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]
