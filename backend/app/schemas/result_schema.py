#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pydantic import BaseModel

from .user_schema import User


class BaseResult(BaseModel):
    code: int
    message: str


class ResultUser(BaseResult):
    data: User | None = None
