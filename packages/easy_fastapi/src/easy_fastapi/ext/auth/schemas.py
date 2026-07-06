"""auth 路由数据契约。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """JSON body 登录请求（可选；路由默认用 OAuth2PasswordRequestForm）。"""

    model_config = ConfigDict(extra="forbid")

    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class AuthUserOut(BaseModel):
    """/me 返回的安全用户视图（不含 hashed_password）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    is_active: bool = True
    scopes: list[str] = Field(default_factory=list)


class TokenPayload(BaseModel):
    """JWT 解码后的载荷（声明 RFC 7519 全部标准字段，皆可为空）。

    access/refresh 共用，靠 type 字段区分。
    """

    # ── RFC 7519 标准注册声明 ──
    iss: str | None = None  # issuer 签发者
    sub: str | None = None  # subject 主题（用户标识）
    aud: str | list[str] | None = None  # audience 接收者
    exp: int | None = None  # expiration time 过期（Unix 时间戳）
    nbf: int | None = None  # not before 生效时间
    iat: int | None = None  # issued at 签发时间
    jti: str | None = None  # JWT ID 唯一标识

    # ── 业务字段 ──
    type: Literal["access", "refresh"] | None = None  # 令牌类型
    scopes: list[str] | None = None  # 令牌签发时携带的 scopes（可选）
