from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class BrandingColors(ApiModel):
    accent: str
    header_background: str = Field(alias="headerBackground")


class BrandingAuthentication(ApiModel):
    heading: str
    description: str
    connect_label: str = Field(alias="connectLabel")


class BrandingLinks(ApiModel):
    privacy: str | None
    terms: str | None
    source: str | None
    support: str | None


class BrandingManifest(ApiModel):
    preset: str
    product_name: str = Field(alias="productName")
    short_name: str = Field(alias="shortName")
    logo_url: str | None = Field(alias="logoUrl")
    favicon_url: str | None = Field(alias="faviconUrl")
    title_template: str = Field(alias="titleTemplate")
    colors: BrandingColors
    authentication: BrandingAuthentication
    links: BrandingLinks
    notice: str | None
    provider_display_names: dict[str, str] = Field(alias="providerDisplayNames")


class InstanceMeta(ApiModel):
    name: str
    base_url: str = Field(alias="baseUrl")
    branding: BrandingManifest
    registration_enabled: bool = Field(alias="registrationEnabled")
    version: str


class AuthProvider(ApiModel):
    id: str
    display_name: str = Field(alias="displayName")
    enabled: bool
    supports_registration: bool = Field(alias="supportsRegistration")


class AuthMethods(ApiModel):
    password: bool
    passkey: bool
    two_factor: bool = Field(alias="twoFactor")
    providers: list[AuthProvider]


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
