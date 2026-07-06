"""auth 扩展配置。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class CookieOptions(BaseModel):
    """refresh_token cookie 配置（token_transport=cookie 时生效）。

    path 默认 None：运行时按 token_prefix 派生为 '{prefix}/refresh'，
    避免 token_prefix 改动后 cookie path 不匹配导致浏览器不回传。
    显式配置 path 时覆盖该派生值。
    """

    model_config = ConfigDict(extra="forbid")

    name: str = "refresh_token"
    path: str | None = None
    domain: str | None = None
    secure: bool = False
    httponly: bool = True
    samesite: Literal["strict", "lax", "none"] = "lax"


class AuthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    secret: str
    algorithm: str = "HS256"
    access_expire_minutes: int = 60 * 24
    refresh_expire_days: int = 7
    token_prefix: str = "/auth"
    enable_refresh: bool = True
    token_transport: Literal["body", "cookie"] = "body"
    cookie: CookieOptions = CookieOptions()
    scope_match: Literal["any", "all"] = "any"  # scopes 匹配策略：any=交集(OR，默认)，all=子集(AND)

    @field_validator("secret")
    @classmethod
    def _secret_min_length(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError(f"secret 长度不能少于 16 个字符（当前：{len(v)}字符）。请使用强随机密钥。")
        return v
