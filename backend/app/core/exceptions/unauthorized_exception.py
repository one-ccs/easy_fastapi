#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import HTTPException


class UnauthorizedException(HTTPException):

    def __init__(self, detail='请登录后操作', status_code=401) -> None:
        super().__init__(status_code, detail, {
            'WWW-Authenticate': 'Bearer',
        })
