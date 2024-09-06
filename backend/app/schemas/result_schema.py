#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pydantic import BaseModel

from .user_schema import User, LoginResponse


class BaseResult(BaseModel):
    code: int
    message: str

class ResultLogin(BaseResult):
    data: LoginResponse

class ResultUser(BaseResult):
    data: User | None = None
