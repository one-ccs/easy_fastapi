#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tortoise import Model, fields
from easy_pyoc import ObjectUtil

from app.core import ExtendedCRUD


class Role(ObjectUtil.MagicClass, ExtendedCRUD, Model):
    """角色表"""

    id        = fields.IntField(primary_key=True, description='角色 id')
    role      = fields.CharField(max_length=16, db_index=True, description='角色名称')
    role_desc = fields.CharField(max_length=32, description='角色描述')

    users: fields.ManyToManyRelation['User'] # type: ignore
