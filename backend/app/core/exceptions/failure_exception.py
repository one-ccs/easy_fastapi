#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import HTTPException


class FailureException(HTTPException):

    def __init__(self, detail='请求失败', status_code=400) -> None:
        super().__init__(status_code, detail)
