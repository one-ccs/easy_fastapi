#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import HTTPException


class TODOException(HTTPException):

    def __init__(self, detail='该方法暂未实现', status_code=400) -> None:
        super().__init__(status_code, detail)
