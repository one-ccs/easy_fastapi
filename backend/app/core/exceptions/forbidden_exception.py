#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import HTTPException


class ForbiddenException(HTTPException):

    def __init__(self, detail='您无权进行此操作', status_code=403) -> None:
        super().__init__(status_code, detail)
