#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pydantic import BaseModel

from .user_schema import UserInfo, UserLogin
from .role_schema import Role


class BaseResult(BaseModel):
    code: int
    message: str


class ResultLogin(BaseResult):
    data: UserLogin


class ResultUser(BaseResult):
    data: UserInfo | None = None


class ResultRoles(BaseResult):
    data: list[Role] | None = None
