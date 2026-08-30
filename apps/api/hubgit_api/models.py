from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(32), default="member")
    avatar_url: Mapped[str] = mapped_column(String(500), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    sessions: Mapped[list[Session]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def public(self) -> dict[str, Any]:
        return {
            "id": f"usr_{self.id}",
            "kind": "user",
            "login": self.login,
            "displayName": self.display_name,
            "email": self.email,
            "avatarUrl": self.avatar_url or f"https://api.dicebear.com/9.x/identicon/svg?seed={self.login}",
            "bio": self.bio,
            "role": self.role,
            "createdAt": self.created_at.isoformat(),
        }


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_token: Mapped[str] = mapped_column(String(80))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped[User] = relationship(back_populates="sessions")


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (UniqueConstraint("owner", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    visibility: Mapped[str] = mapped_column(String(20), default="public")
    default_branch: Mapped[str] = mapped_column(String(160), default="main")
    language: Mapped[str | None] = mapped_column(String(80), nullable=True)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    resources: Mapped[list[Resource]] = relationship(back_populates="repository", cascade="all, delete-orphan")

    def public(self, viewer: User | None = None) -> dict[str, Any]:
        can_admin = viewer is not None and (viewer.login == self.owner or viewer.role == "admin")
        can_write = viewer is not None and (can_admin or viewer.role == "maintainer")
        return {
            "id": f"repo_{self.id}",
            "kind": "repository",
            "owner": {"login": self.owner, "kind": "user"},
            "name": self.name,
            "fullName": f"{self.owner}/{self.name}",
            "description": self.description,
            "visibility": self.visibility,
            "defaultBranch": self.default_branch,
            "language": self.language,
            "stargazerCount": self.stars,
            "forkCount": self.forks,
            "archived": self.archived,
            "cloneUrls": {
                "https": f"https://git.example.test/{self.owner}/{self.name}.git",
                "ssh": f"git@git.example.test:{self.owner}/{self.name}.git",
            },
            "permissions": {"read": True, "triage": viewer is not None, "write": can_write, "admin": can_admin},
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
        }


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (UniqueConstraint("repository_id", "kind", "key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(48), index=True)
    key: Mapped[str] = mapped_column(String(240), index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    repository: Mapped[Repository] = relationship(back_populates="resources")

    def public(self) -> dict[str, Any]:
        result = dict(self.data)
        result.setdefault("id", f"{self.kind}_{self.id}")
        result.setdefault("kind", self.kind)
        result.setdefault("createdAt", self.created_at.isoformat())
        result.setdefault("updatedAt", self.updated_at.isoformat())
        return result


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reason: Mapped[str] = mapped_column(String(48))
    unread: Mapped[bool] = mapped_column(Boolean, default=True)
    subject: Mapped[dict[str, Any]] = mapped_column(JSON)
    repository: Mapped[dict[str, Any]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    def public(self) -> dict[str, Any]:
        return {
            "id": f"notification_{self.id}",
            "kind": "notification",
            "reason": self.reason,
            "unread": self.unread,
            "subject": self.subject,
            "repository": self.repository,
            "updatedAt": self.updated_at.isoformat(),
        }

