#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import HTTPException


class FailureException(HTTPException):

    def __init__(self, message='请求失败', status_code=400) -> None:
        self.message = message
        self.status_code = status_code
