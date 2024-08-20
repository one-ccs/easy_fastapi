#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import HTTPException


class TODOException(HTTPException):

    def __init__(self, message='该方法暂未实现', status_code=400) -> None:
        self.message = message
        self.status_code = status_code
