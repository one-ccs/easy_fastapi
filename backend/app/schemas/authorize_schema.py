#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime
from dataclasses import dataclass

from fastapi import Form
from pydantic import BaseModel, ConfigDict, EmailStr

from .user_schema import UserInfo
from app.utils import DateTimeUtil


class LoginOut(BaseModel):
    user_info: UserInfo
    token_type: str
    access_token: str
    refresh_token: str

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: DateTimeUtil.strftime(v),
        },
    )

@dataclass
class RegisterIn():
    email: EmailStr = Form(None)
    username: str   = Form(None)
    password: str   = Form()


class RegisterOut(BaseModel):
    username: str


class RefreshOut(BaseModel):
    token_type: str
    refresh_token: str
