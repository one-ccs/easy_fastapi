#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenUser(BaseModel):
    id: int
    username: str
    is_active: bool
    exp: datetime
