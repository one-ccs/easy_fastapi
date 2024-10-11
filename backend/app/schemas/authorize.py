#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import dataclass

from fastapi import Form
from pydantic import BaseModel, EmailStr

from .user import UserInfo


class TokenOut(BaseModel):
    token_type: str
    access_token: str
    refresh_token: str


class LoginOut(BaseModel):
    user_info: UserInfo
    token_type: str
    access_token: str
    refresh_token: str


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
