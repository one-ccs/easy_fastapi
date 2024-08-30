#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import Request, HTTPException

from .exceptions import TODOException, FailureException
from app.core import Result
from app import app


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    return Result.failure('服务器错误，请联系管理员')


@app.exception_handler(HTTPException)
async def http_exception(request: Request, exc: HTTPException):
    match exc.status_code:
        case 401:
            if type(exc) == HTTPException:
                return Result.unauthorized()
            return Result.unauthorized(message=exc.detail)
        case 403:
            return Result.forbidden()
        case 404:
            return Result.error_404()
        case 405:
            return Result.method_not_allowed()
        case _:
            return Result.failure(code=exc.status_code)


@app.exception_handler(TODOException)
async def todo_exception_handler(request: Request, exc: TODOException):
    return Result.failure(exc.detail)


@app.exception_handler(FailureException)
async def todo_exception_handler(request: Request, exc: FailureException):
    return Result.failure(exc.detail)
