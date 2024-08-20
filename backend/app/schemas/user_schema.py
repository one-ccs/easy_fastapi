#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pydantic import BaseModel
from datetime import datetime

from app.utils import DateTimeUtil
from .role_schema import Role


class UserBase(BaseModel):
    email: str
    username: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    roles: list[Role] = []

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: DateTimeUtil.strftime(v)
        }
