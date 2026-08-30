from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class LoginInput(ApiModel):
    login: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class RegisterInput(ApiModel):
    login: str = Field(pattern=r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$", max_length=39)
    display_name: str = Field(alias="displayName", min_length=1, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class RecoveryInput(ApiModel):
    email: EmailStr


class ResetInput(ApiModel):
    token: str
    password: str = Field(min_length=8, max_length=256)


class IssueInput(ApiModel):
    title: str = Field(min_length=1, max_length=256)
    body: str = Field(default="", max_length=100_000)
    labels: list[str] = []
    assignees: list[str] = []


class CommentInput(ApiModel):
    body: str = Field(min_length=1, max_length=100_000)


class PullInput(ApiModel):
    title: str = Field(min_length=1, max_length=256)
    body: str = Field(default="", max_length=100_000)
    head: str
    base: str = "main"
    draft: bool = False


class ReviewInput(ApiModel):
    body: str = ""
    event: str = Field(pattern=r"^(comment|approve|request_changes)$")
    comments: list[dict[str, Any]] = []


class MergeInput(ApiModel):
    method: str = Field(default="merge", pattern=r"^(merge|squash|rebase)$")
    commit_title: str | None = Field(default=None, alias="commitTitle", max_length=256)


class RepositoryPatch(ApiModel):
    description: str | None = Field(default=None, max_length=500)
    default_branch: str | None = Field(default=None, alias="defaultBranch", max_length=160)
    visibility: str | None = Field(default=None, pattern=r"^(public|private|internal)$")
    archived: bool | None = None


class SearchResult(BaseModel):
    items: list[dict[str, Any]]
    page_info: dict[str, Any] = Field(alias="pageInfo")
    total_count: int = Field(alias="totalCount")

