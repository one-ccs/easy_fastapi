#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlmodel import SQLModel, Field

class RelUserRole(SQLModel, table=True):
    """用户角色关联表"""
    __tablename__ = "rel_user_role"

    user_id: int | None = Field(None, foreign_key="user.id", primary_key=True)
    role_id: int | None = Field(None, foreign_key="role.id", primary_key=True)
