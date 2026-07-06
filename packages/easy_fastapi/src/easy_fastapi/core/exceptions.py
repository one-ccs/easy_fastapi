"""easy_fastapi 异常体系。

分两层：
- 框架异常（EasyFastAPIError 体系）：扩展装配/配置等框架内部错误。
- 业务 HTTP 异常（HTTPException 体系）：生成项目业务层用，经 core.handlers 统一处理。
"""

from __future__ import annotations

from fastapi import HTTPException

# ── 统一英文消息常量（exceptions / result / handlers 共用，单一来源） ──

MSG_FAILURE = "Request failed"
MSG_UNAUTHORIZED = "Please login first"
MSG_FORBIDDEN = "Permission denied"
MSG_NOT_FOUND = "Resource not found"
MSG_METHOD_NOT_ALLOWED = "Method not allowed"
MSG_BAD_REQUEST = "Bad request"

# ── 框架异常 ──


class EasyFastAPIError(Exception):
    """所有 easy_fastapi 框架异常的根基类。"""


class ExtensionError(EasyFastAPIError):
    """扩展装配 / ExtensionContext / use() / ctx 相关错误。"""


class ConfigError(EasyFastAPIError):
    """配置加载 / 校验 / 文件缺失相关错误。"""


# ── 业务 HTTP 异常 ──


class FailureException(HTTPException):
    """通用业务失败（400）。

    status_code: HTTP 状态码（由 handler 映射到响应）
    code: 自定义业务码（可选；设值后 handler 将其作为 JSON body code，不再按策略自动推算）
    """

    detail: str = MSG_FAILURE
    status_code: int = 400
    headers: dict[str, str] | None = None

    def __init__(
        self,
        detail: str | None = None,
        *,
        status_code: int | None = None,
        code: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            status_code or self.status_code,
            detail or self.detail,
            headers if headers is not None else self.headers,
        )
        self.code = code


class UnauthorizedException(FailureException):
    """未认证（401）。"""

    detail = MSG_UNAUTHORIZED
    status_code = 401
    headers = {"WWW-Authenticate": "Bearer"}

    def __init__(
        self,
        detail: str | None = None,
        *,
        status_code: int | None = None,
        code: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        # headers 不用 `or` 判断：headers={} 是合法的显式空值，不应回退到类默认
        effective_headers = headers if headers is not None else self.headers.copy()
        super().__init__(
            detail or self.detail,
            status_code=status_code or self.status_code,
            headers=effective_headers,
        )
        self.code = code


class ForbiddenException(FailureException):
    """无权限（403）。"""

    detail = MSG_FORBIDDEN
    status_code = 403


class NotFoundException(FailureException):
    """资源不存在（404）。"""

    detail = MSG_NOT_FOUND
    status_code = 404
