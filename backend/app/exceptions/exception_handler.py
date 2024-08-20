#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import Request, HTTPException

from app.utils import Result
from app import app
from . import TODOException, FailureException


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    return Result.failure('服务器错误，请联系管理员')


@app.exception_handler(HTTPException)
async def http_exception(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return Result.unauthorized()
    elif exc.status_code == 403:
        return Result.forbidden()
    elif exc.status_code == 404:
        return Result.error_404()
    elif exc.status_code == 405:
        return Result.method_not_allowed()
    else:
        return Result.failure(code=exc.status_code)


@app.exception_handler(TODOException)
async def todo_exception_handler(request: Request, exc: TODOException):
    return Result.failure(exc.message)


@app.exception_handler(FailureException)
async def todo_exception_handler(request: Request, exc: FailureException):
    return Result.failure(exc.message)
