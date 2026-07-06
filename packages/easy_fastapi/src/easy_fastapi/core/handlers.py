"""异常 handler 绑定。

在 EasyFastAPI._init_app 中自动调用 binding_exception_handler(app)，
将框架层异常 + 业务 HTTP 异常统一映射到 ResponseResult 响应。

ORM 特定异常（如 Tortoise BaseORMException）不在此处注册，
由各 ORM 扩展在 init_app 中自行注册。
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .exceptions import (
    MSG_BAD_REQUEST,
    FailureException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from .result import ResponseResult


def binding_exception_handler(app: FastAPI) -> None:
    """绑定全局异常 handler 到 FastAPI 应用。"""

    # ── 服务器异常 ──

    @app.exception_handler(Exception)
    async def server_exception_handler(request: Request, exc: Exception):
        return ResponseResult(
            "Internal server error",
            status_code=500,
            exc=exc,
        )

    # ── HTTP 异常（starlette/fastapi 基类）──

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        match exc.status_code:
            case 401:
                return ResponseResult.unauthorized(str(exc.detail), headers=exc.headers)
            case 403:
                return ResponseResult.forbidden(str(exc.detail), headers=exc.headers)
            case 404:
                return ResponseResult.not_found(str(exc.detail), headers=exc.headers)
            case 405:
                return ResponseResult.method_not_allowed(str(exc.detail), headers=exc.headers)
            case _:
                # 保留原始 status_code（如 409 Conflict 等）
                return ResponseResult(
                    str(exc.detail),
                    status_code=exc.status_code,
                    headers=exc.headers,
                )

    # ── 请求参数校验异常 ──

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
        if app.debug:
            return ResponseResult.failure(MSG_BAD_REQUEST, exc=exc)
        return ResponseResult.failure(MSG_BAD_REQUEST)

    @app.exception_handler(PydanticValidationError)
    async def validation_exception_handler(request: Request, exc: PydanticValidationError):
        if app.debug:
            return ResponseResult.failure(MSG_BAD_REQUEST, exc=exc)
        return ResponseResult.failure(MSG_BAD_REQUEST)

    # ── 业务 HTTP 异常 ──
    # 子类（UnauthorizedException/ForbiddenException/NotFoundException）有独立 handler，
    # 此处只处理直接构造的 FailureException（含自定义 status_code 场景）。

    @app.exception_handler(FailureException)
    async def failure_exception_handler(request: Request, exc: FailureException):
        return ResponseResult(exc.detail, code=exc.code, status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(UnauthorizedException)
    async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
        return ResponseResult.unauthorized(exc.detail, headers=exc.headers)

    @app.exception_handler(ForbiddenException)
    async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
        return ResponseResult.forbidden(exc.detail, headers=exc.headers)

    @app.exception_handler(NotFoundException)
    async def notfound_exception_handler(request: Request, exc: NotFoundException):
        return ResponseResult.not_found(exc.detail, headers=exc.headers)
