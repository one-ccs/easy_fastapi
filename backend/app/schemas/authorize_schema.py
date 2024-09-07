#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pydantic import BaseModel


class RefreshToken(BaseModel):
    token_type: str
    refresh_token: str


class Register(BaseModel):
    username: str
