#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pydantic import BaseModel
from datetime import datetime

from app.utils import DateTimeUtil
from .role_schema import Role


class UserBase(BaseModel):
    email: str
    username: str

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: DateTimeUtil.strftime(v)
        }


class UserCreate(UserBase):
    email: str | None = None
    username: str | None = None
    password: str


class UserInDB(UserBase):
    id: int
    hashed_password: str
    token: str
    avatar_url: str
    is_active: bool
    created_at: datetime


class User(UserBase):
    id: int
    roles: list[Role] = []
    is_active: bool
