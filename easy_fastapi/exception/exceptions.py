#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Optional

from fastapi import HTTPException


class ConfigException(Exception):
    pass


class BaseException(HTTPException):
    detail: str                    = '请求失败'
    status_code: int               = 400
    headers: dict[str, str] | None = None

    def __init__(self, detail: Optional[str] = None, *, status_code: Optional[int] = None, headers: Optional[dict[str, str]] = None) -> None:
        super().__init__(status_code or self.status_code, detail or self.detail, headers or self.headers)


class TODOException(BaseException):
    detail      = '该方法暂未实现'
    status_code = 400


class FailureException(BaseException):
    detail      = '请求失败'
    status_code = 400


class UnauthorizedException(BaseException):
    detail      = '请登录后操作'
    status_code = 401
    headers     = {
        'WWW-Authenticate': 'Bearer',
    }


class ForbiddenException(BaseException):
    detail      = '您无权进行此操作'
    status_code = 403


class NotFoundException(BaseException):
    detail      = '未找到请求的资源'
    status_code = 404
