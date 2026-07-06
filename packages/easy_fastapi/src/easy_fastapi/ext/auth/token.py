"""JWT 令牌服务（PyJWT）。

create_access_token / create_refresh_token 编码 JWT（含 sub + type + jti + exp）。
decode 解码并验证签名/过期；失败抛 PyJWT 异常，由调用方处理。
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from easy_fastapi.core.extras import require
from easy_fastapi.ext.auth.schemas import TokenPayload

jwt = require("pyjwt", "jwt")

# 允许的 JWT 算法白名单（防止配置误用 "none" 或不对称算法）
_ALLOWED_ALGORITHMS = {"HS256", "HS384", "HS512"}


class TokenService:
    def __init__(
        self,
        *,
        secret: str,
        algorithm: str = "HS256",
        access_expire_minutes: int = 60 * 24,
        refresh_expire_days: int = 7,
    ) -> None:
        if algorithm not in _ALLOWED_ALGORITHMS:
            raise ValueError(f"不支持的 JWT 算法：'{algorithm}'（允许：{sorted(_ALLOWED_ALGORITHMS)}）")
        self._secret = secret
        self._algorithm = algorithm
        self._access_minutes = access_expire_minutes
        self._refresh_days = refresh_expire_days

    @property
    def refresh_max_age(self) -> int:
        """refresh token 的最大存活时间（秒），用于 cookie max-age。"""
        return self._refresh_days * 86400

    @property
    def access_max_age(self) -> int:
        """access token 的最大存活时间（秒），用于黑名单 TTL 兜底。"""
        return self._access_minutes * 60

    def create_access_token(self, sub: str) -> str:
        now = datetime.now(tz=timezone.utc)
        exp = now + timedelta(minutes=self._access_minutes)
        return jwt.encode(
            {"sub": sub, "type": "access", "jti": secrets.token_hex(16), "iat": now, "exp": exp},
            self._secret,
            algorithm=self._algorithm,
        )

    def create_refresh_token(self, sub: str) -> str:
        now = datetime.now(tz=timezone.utc)
        exp = now + timedelta(days=self._refresh_days)
        return jwt.encode(
            {"sub": sub, "type": "refresh", "jti": secrets.token_hex(16), "iat": now, "exp": exp},
            self._secret,
            algorithm=self._algorithm,
        )

    def decode(self, token: str) -> TokenPayload:
        """解码并验证 JWT。

        成功返回 TokenPayload；失败抛 PyJWT 异常：
          ExpiredSignatureError / InvalidSignatureError / DecodeError / InvalidTokenError / PyJWTError
        """
        payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        return TokenPayload(**payload)
