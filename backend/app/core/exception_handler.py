#!/usr/bin/env python
# -*- coding: utf-8 -*-
import jwt
from starlette.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi import Request

from .exceptions import (
    TODOException,
    FailureException,
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
)
from app.core import JSONResponseResult, logger
from app import app

################## 服务器异常 ##################


@app.exception_handler(Exception)
async def server_exception_handler(request: Request, exc: Exception):
    logger.warning(msg=f"服务器错误", exc_info=exc)
    return JSONResponseResult('服务器错误，请联系管理员', code=500)


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
            logger.warning(msg=f"未知 HTTP 错误", exc_info=exc)
            return JSONResponseResult.failure('未知 HTTP 错误')


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    method = request.scope["method"]
    path = request.scope["path"]
    logger.info(msg=f"'{method} {path}' 请求参数有误 {exc.errors()}")
    return JSONResponseResult.failure('请求参数有误')


################## JWT 异常 ##################


@app.exception_handler(jwt.ExpiredSignatureError)
async def jwt_exception_handler_1(request: Request, exc: jwt.ExpiredSignatureError):
    return JSONResponseResult.unauthorized('令牌已过期')


@app.exception_handler(jwt.InvalidSignatureError)
async def jwt_exception_handler_2(request: Request, exc: jwt.InvalidSignatureError):
    return JSONResponseResult.unauthorized('无效的签名')


@app.exception_handler(jwt.DecodeError)
async def jwt_exception_handler_3(request: Request, exc: jwt.DecodeError):
    return JSONResponseResult.unauthorized('令牌解析失败')


@app.exception_handler(jwt.InvalidTokenError)
async def jwt_exception_handler_4(request: Request, exc: jwt.InvalidTokenError):
    return JSONResponseResult.unauthorized('无效的访问令牌')


@app.exception_handler(jwt.PyJWTError)
async def jwt_exception_handler_5(request: Request, exc: jwt.PyJWTError):
    logger.warning(msg=f"未知令牌错误", exc_info=exc)
    return JSONResponseResult.unauthorized('未知令牌错误')


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
