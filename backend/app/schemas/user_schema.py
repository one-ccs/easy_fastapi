#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from app.utils import DateTimeUtil
from .role_schema import Role


class UserBase(BaseModel):
    email: str | None = None
    username: str | None = None


class UserCreate(UserBase):
    password: str


class UserLogin(UserCreate):
    pass


class User(UserBase):
    roles: list[Role] = []

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: DateTimeUtil.strftime(v),
        },
    )

class LoginResponse(UserBase):
    avatar_url: str | None = None
    token_type: str = "bearer"
    access_token: str
    refresh_token: str
