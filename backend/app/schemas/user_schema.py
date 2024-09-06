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


class UserInfo(UserBase):
    avatar_url: str | None = None
    created_at: datetime
    roles: list[Role] = []


class UserLogin(BaseModel):
    user_info: UserInfo
    token_type: str
    access_token: str
    refresh_token: str

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: DateTimeUtil.strftime(v),
        },
    )
