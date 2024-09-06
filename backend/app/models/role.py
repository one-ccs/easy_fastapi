#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlmodel import SQLModel, Field

from app.core import ToolClass


class Role(SQLModel, ToolClass, table=True):
    __tablename__ = 'role'

    id: int | None = Field(None, primary_key=True)
    role: str
    role_desc: str
