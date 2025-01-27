#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError

from tortoise.exceptions import (
    ValidationError as TortoiseValidationError,
    BaseORMException,
)

from .exceptions import (
    TODOException,
    FailureException,
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
)
from ..result import JSONResponseResult


def binding_exception_handler(app: FastAPI):
    ################## 服务器异常 ##################

    @app.exception_handler(Exception)
    async def server_exception_handler(request: Request, exc: Exception):
        return JSONResponseResult.failure_with_id('服务器错误，请联系管理员', exc=exc, code=500)

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
                return JSONResponseResult.failure_with_id('未知 HTTP 错误', exc=exc)

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
        if app.debug:
            return JSONResponseResult.failure_with_id('请求参数有误', exc=exc)
        return JSONResponseResult.failure('请求参数有误')

    @app.exception_handler(PydanticValidationError)
    async def validation_exception_handler(request: Request, exc: PydanticValidationError):
        if app.debug:
            return JSONResponseResult.failure_with_id('请求参数有误', exc=exc)
        return JSONResponseResult.failure('请求参数有误')

    ################## Tortoise ORM 异常 ##################

    @app.exception_handler(TortoiseValidationError)
    async def tortoise_validation_exception_handler(request: Request, exc: TortoiseValidationError):
        return JSONResponseResult.failure(f'Tortoise ORM 验证错误: "{exc}"')

    @app.exception_handler(BaseORMException)
    async def tortoise_orm_exception_handler(request: Request, exc: BaseORMException):
        return JSONResponseResult.failure_with_id('未知 Tortoise ORM 错误', exc=exc)

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
