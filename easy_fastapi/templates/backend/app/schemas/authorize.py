#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import dataclass

from fastapi import Form
from pydantic import BaseModel, EmailStr

from .user import User


class TokenOut(BaseModel):
    token_type: str
    access_token: str
    refresh_token: str


class LoginOut(BaseModel):
    user: User
    token_type: str
    access_token: str
    refresh_token: str


@dataclass
class Register():
    email: EmailStr = Form(None)
    username: str   = Form(None)
    password: str   = Form()


class RegisterOut(BaseModel):
    username: str


class RefreshTokenOut(BaseModel):
    token_type: str
    refresh_token: str
