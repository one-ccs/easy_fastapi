#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import HTTPException


class NotFoundException(HTTPException):

    def __init__(self, detail='什么都没有', status_code=404) -> None:
        super().__init__(status_code, detail)
