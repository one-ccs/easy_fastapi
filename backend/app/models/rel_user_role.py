#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlmodel import SQLModel, Field, Relationship


class RelUserRole(SQLModel, table=True):
    """用户角色关联表"""
