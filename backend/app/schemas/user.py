#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_serializer

from .role import Role
from app.utils import DateTimeUtil


class UserBase(BaseModel):
    email: EmailStr | None = None
    username: str | None = None


class UserCreate(UserBase):
    password: str


class UserInfo(UserBase):
    avatar_url: str | None = None
    created_at: datetime
    roles: list[Role] = []


    @field_serializer('created_at')
    def serialize_created_at(self, value: datetime) -> str:
        return DateTimeUtil.strftime(value)


class UserModify(UserBase):
    id: int
    password: str | None = None
    avatar_url: str | None = None
    is_active: bool | None = None


class UserLogin(BaseModel):
    user_info: UserInfo
    token_type: str
    access_token: str
    refresh_token: str
