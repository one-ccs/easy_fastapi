#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlmodel import SQLModel, Field, Relationship

from .rel_user_role import RelUserRole


class Role(SQLModel, table=True):
    __tablename__ = 'role'

    id: int | None = Field(None, primary_key=True)
    role: str | None = Field(None, max_length=16)
    role_desc: str | None = Field(None, max_length=32)

    users: list['User'] = Relationship(back_populates='roles', link_model=RelUserRole)
