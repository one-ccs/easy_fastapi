#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import Request
from starlette.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidSignatureError,
    DecodeError,
    InvalidTokenError,
    PyJWTError,
)
from tortoise.exceptions import (
    ValidationError as TortoiseValidationError,
    BaseORMException,
)
from uuid import uuid4

from easy_fastapi import (
    TODOException,
    FailureException,
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    JSONResponseResult,
    uvicorn_logger,
)

from ..main import app

################## 服务器异常 ##################


@app.exception_handler(Exception)
async def server_exception_handler(request: Request, exc: Exception):
    uuid = uuid4().hex
    uvicorn_logger.error(msg=f"服务器错误: {uuid}", exc_info=exc)
    return JSONResponseResult('服务器错误，请联系管理员', data=uuid, code=500)


################## HTTP 异常 ##################


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    match exc.status_code:
        case 401:
            return JSONResponseResult.unauthorized()
        case 403:
            return JSONResponseResult.forbidden()
        case 404:
            return JSONResponseResult.error_404()
        case 405:
            return JSONResponseResult.method_not_allowed()
        case _:
            uvicorn_logger.error(msg=f"未知 HTTP 错误", exc_info=exc)
            return JSONResponseResult.failure('未知 HTTP 错误')


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    method = request.scope["method"]
    path = request.scope["path"]
    uvicorn_logger.warning(msg=f"'{method} {path}' 请求参数有误 {exc.errors()}")
    return JSONResponseResult.failure('请求参数有误')


@app.exception_handler(PydanticValidationError)
async def validation_exception_handler(request: Request, exc: PydanticValidationError):
    method = request.scope["method"]
    path = request.scope["path"]
    uvicorn_logger.warning(msg=f"'{method} {path}' 请求参数有误 {exc.errors()}")
    return JSONResponseResult.failure('请求参数有误')


################## JWT 异常 ##################


@app.exception_handler(ExpiredSignatureError)
async def jwt_exception_handler_1(request: Request, exc: ExpiredSignatureError):
    return JSONResponseResult.unauthorized('令牌已过期')


@app.exception_handler(InvalidSignatureError)
async def jwt_exception_handler_2(request: Request, exc: InvalidSignatureError):
    return JSONResponseResult.unauthorized('无效的签名')


@app.exception_handler(DecodeError)
async def jwt_exception_handler_3(request: Request, exc: DecodeError):
    return JSONResponseResult.unauthorized('令牌解析失败')


@app.exception_handler(InvalidTokenError)
async def jwt_exception_handler_4(request: Request, exc: InvalidTokenError):
    return JSONResponseResult.unauthorized('无效的访问令牌')


@app.exception_handler(PyJWTError)
async def jwt_exception_handler_5(request: Request, exc: PyJWTError):
    uvicorn_logger.error(msg=f"未知令牌错误", exc_info=exc)
    return JSONResponseResult.unauthorized('未知令牌错误')


################## Tortoise ORM 异常 ##################


@app.exception_handler(TortoiseValidationError)
async def tortoise_validation_exception_handler(request: Request, exc: TortoiseValidationError):
    return JSONResponseResult.failure(f'Tortoise ORM 验证错误: "{exc}"')


@app.exception_handler(BaseORMException)
async def tortoise_orm_exception_handler(request: Request, exc: BaseORMException):
    uvicorn_logger.error(msg=f"未知 Tortoise ORM 错误", exc_info=exc)
    return JSONResponseResult.failure('未知 Tortoise ORM 错误')


################## 自定义异常 ##################


@app.exception_handler(TODOException)
async def todo_exception_handler(request: Request, exc: TODOException):
    return JSONResponseResult.failure(exc.detail)


@app.exception_handler(FailureException)
async def failure_exception_handler(request: Request, exc: FailureException):
    return JSONResponseResult.failure(exc.detail)


@app.exception_handler(UnauthorizedException)
async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
    return JSONResponseResult.unauthorized(exc.detail)


@app.exception_handler(ForbiddenException)
async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
    return JSONResponseResult.forbidden(exc.detail)


@app.exception_handler(NotFoundException)
async def notfound_exception_handler(request: Request, exc: NotFoundException):
    return JSONResponseResult.error_404(exc.detail)
