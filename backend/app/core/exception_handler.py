#!/usr/bin/env python
# -*- coding: utf-8 -*-
import jwt
from fastapi import Request, HTTPException

from .exceptions import (
    TODOException,
    FailureException,
    UnauthorizedException,
    ForbiddenException,
)
from app.core import Result
from app import app


@app.exception_handler(Exception)
async def server_exception_handler(request: Request, exc: Exception):
    return Result.failure('服务器错误，请联系管理员')


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    match exc.status_code:
        case 401:
            return Result.unauthorized()
        case 403:
            return Result.forbidden()
        case 404:
            return Result.error_404()
        case 405:
            return Result.method_not_allowed()
        case _:
            return Result.failure(f'未知 HTTP 错误, {exc.detail}', code=exc.status_code)


@app.exception_handler(jwt.ExpiredSignatureError)
async def jwt_exception_handler_1(request: Request, exc: jwt.ExpiredSignatureError):
    return Result.failure('令牌已过期', code=401.8)


@app.exception_handler(jwt.InvalidSignatureError)
async def jwt_exception_handler_2(request: Request, exc: jwt.InvalidSignatureError):
    return Result.unauthorized('无效的签名')


@app.exception_handler(jwt.DecodeError)
async def jwt_exception_handler_3(request: Request, exc: jwt.DecodeError):
    return Result.unauthorized('令牌解析失败')


@app.exception_handler(jwt.InvalidTokenError)
async def jwt_exception_handler_4(request: Request, exc: jwt.InvalidTokenError):
    return Result.unauthorized('无效的访问令牌')


@app.exception_handler(jwt.PyJWTError)
async def jwt_exception_handler_5(request: Request, exc: jwt.PyJWTError):
    return Result.failure('未知令牌错误')


@app.exception_handler(TODOException)
async def todo_exception_handler(request: Request, exc: TODOException):
    return Result.failure(exc.detail)


@app.exception_handler(FailureException)
async def failure_exception_handler(request: Request, exc: FailureException):
    return Result.failure(exc.detail)


@app.exception_handler(UnauthorizedException)
async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
    return Result.unauthorized(exc.detail)


@app.exception_handler(ForbiddenException)
async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
    return Result.forbidden(exc.detail)
