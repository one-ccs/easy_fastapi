#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tortoise import Model, fields
from easy_pyoc import ObjectUtil

from app.core import ExtendedCRUD


class Role(ObjectUtil.MagicClass, ExtendedCRUD, Model):
    """角色表"""

    id        = fields.IntField(primary_key=True)
    role      = fields.CharField(max_length=16, db_index=True)
    role_desc = fields.CharField(max_length=32)
