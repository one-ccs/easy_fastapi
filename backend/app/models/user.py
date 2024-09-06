#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime

from sqlmodel import SQLModel, Field

from app.core import ToolClass
from app.utils import DateTimeUtil


class User(SQLModel, ToolClass, table=True):
    __tablename__ = 'user'

    id: int | None = Field(None, primary_key=True)
    email: str | None = Field(None, unique=True, index=True, max_length=64)
    username: str | None = Field(None, unique=True, index=True, max_length=32)
    hashed_password: str | None = Field(None, max_length=64)
    token: str | None
    avatar_url: str | None
    is_active: bool = Field(True)
    created_at: datetime = Field(default_factory=DateTimeUtil.now)
