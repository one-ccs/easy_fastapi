#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime
from dataclasses import dataclass

from fastapi import Form
from pydantic import BaseModel, EmailStr, field_serializer
from easy_pyoc import DateTimeUtil

from .role import Role


@dataclass
class Register():
    email: EmailStr = Form(None)
    username: str   = Form(None)
    password: str   = Form()


class UserBase(BaseModel):
    email: EmailStr | None = None
    username: str | None = None

    @field_serializer('created_at', check_fields=False)
    def serialize_created_at(self, value: datetime) -> str:
        return DateTimeUtil.strftime(value)


class User(UserBase):
    avatar_url: str | None = None
    created_at: datetime
    roles: list[Role] = []


class UserCreate(UserBase):
    password: str


class UserModify(UserBase):
    id: int
    password: str | None = None
    avatar_url: str | None = None
    is_active: bool | None = None
