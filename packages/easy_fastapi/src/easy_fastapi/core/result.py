"""统一响应模型。

提供三种响应形式：
- BaseResult: Pydantic BaseModel（response_model 声明用 / Result 返回类型）
- Result: 返回 BaseResult 实例（service 层用，FastAPI 自动序列化）
- ResponseResult: 返回 JSONResponse（异常 handler 用）

body code 与 HTTP status_code 分离：由 ResponseCodeStrategy 决定映射。
错误响应可配置自动附加 trace_id（ResponseCodeConfig.trace_id）。
"""

from __future__ import annotations

import logging
from typing import Any, Generic, TypeVar
from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from easy_fastapi.core.exceptions import (
    MSG_FAILURE,
    MSG_FORBIDDEN,
    MSG_METHOD_NOT_ALLOWED,
    MSG_NOT_FOUND,
    MSG_UNAUTHORIZED,
)
from easy_fastapi.core.i18n import _
from easy_fastapi.core.response_code import is_trace_id_enabled

logger = logging.getLogger("easy_fastapi")

DataT = TypeVar("DataT")


class BaseResult(BaseModel, Generic[DataT]):
    """统一响应模型（response_model 用）。"""

    code: int
    message: str
    data: DataT | None = None


class Result:
    """返回 BaseResult 实例（供 service 层使用）。"""

    def __new__(
        cls,
        message: str = "",
        *,
        data: Any | None = None,
        code: int | None = None,
    ) -> BaseResult:
        from easy_fastapi.core.response_code import get_strategy

        strategy = get_strategy()
        body_code = code if code is not None else strategy.success_code(200)
        return BaseResult(code=body_code, message=_(message) or _("Request succeeded"), data=data)

    @classmethod
    def failure(
        cls,
        message: str = MSG_FAILURE,
        *,
        data: Any | None = None,
        code: int | None = None,
    ) -> BaseResult:
        from easy_fastapi.core.response_code import get_strategy

        strategy = get_strategy()
        body_code = code if code is not None else strategy.error_code(400)
        return cls(message, data=data, code=body_code)


class ResponseResult:
    """返回 JSONResponse（供异常 handler / 路由使用）。

    code: JSON body 中的业务码（None=按策略自动计算）
    status_code: HTTP 状态码（None=按 code 推算）
    exc: 异常对象（传入时自动记录 error 日志）
    两者可独立设置，适应不同业务码体系。

    当配置 trace_id=True 时，所有错误响应（status_code >= 400）自动在 data 中附加 trace_id。
    """

    @staticmethod
    def _resolve_codes(*, code: int | None = None, status_code: int | None = None) -> tuple[int, int]:
        """推算 (body_code, http_status)。"""
        from easy_fastapi.core.response_code import get_strategy

        strategy = get_strategy()
        if code is not None and status_code is not None:
            return code, status_code
        if code is not None:
            return code, strategy.http_status_for(code)
        if status_code is not None:
            if 200 <= status_code < 400:
                return strategy.success_code(status_code), status_code
            return strategy.error_code(status_code), status_code
        return strategy.success_code(200), 200

    def __new__(
        cls,
        message: str = "",
        *,
        data: Any | None = None,
        code: int | None = None,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
        exc: Exception | None = None,
    ) -> JSONResponse:
        body_code, http_status = cls._resolve_codes(code=code, status_code=status_code)

        encoded_data = jsonable_encoder(data)

        # ── 错误响应：可配置自动附加 trace_id ──
        trace_id: str | None = None
        if http_status >= 400 and is_trace_id_enabled():
            trace_id = uuid4().hex
            if isinstance(encoded_data, dict):
                encoded_data = {**encoded_data, "id": trace_id}
            else:
                encoded_data = {"id": trace_id}

        # ── 日志记录（传了 exc 时）──
        if exc is not None:
            logger.error(
                "异常请求[%s] - %s - %s",
                trace_id or "-",
                http_status,
                message,
                exc_info=(type(exc), exc, exc.__traceback__),
            )

        return JSONResponse(
            {"code": body_code, "message": _(message) or _("Request succeeded"), "data": encoded_data},
            status_code=http_status,
            headers=headers,
        )

    @classmethod
    def failure(
        cls,
        message: str = MSG_FAILURE,
        *,
        data: Any | None = None,
        code: int | None = None,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
        exc: Exception | None = None,
    ) -> JSONResponse:
        return cls(message, data=data, code=code, status_code=status_code or 400, headers=headers, exc=exc)

    @classmethod
    def unauthorized(
        cls,
        message: str = MSG_UNAUTHORIZED,
        *,
        headers: dict[str, str] | None = None,
    ) -> JSONResponse:
        return cls(message, status_code=401, headers=headers)

    @classmethod
    def forbidden(
        cls,
        message: str = MSG_FORBIDDEN,
        *,
        headers: dict[str, str] | None = None,
    ) -> JSONResponse:
        return cls(message, status_code=403, headers=headers)

    @classmethod
    def not_found(
        cls,
        message: str = MSG_NOT_FOUND,
        *,
        headers: dict[str, str] | None = None,
    ) -> JSONResponse:
        return cls(message, status_code=404, headers=headers)

    @classmethod
    def method_not_allowed(
        cls,
        message: str = MSG_METHOD_NOT_ALLOWED,
        *,
        headers: dict[str, str] | None = None,
    ) -> JSONResponse:
        return cls(message, status_code=405, headers=headers)
