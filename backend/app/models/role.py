#!/usr/bin/env python
# -*- coding: utf-8 -*-
from enum import Enum

from tortoise import Model, fields

from app.utils import ObjectUtil


class EnumRole(str, Enum):
    guest = 'guest'
    user = 'user'
    admin = 'admin'


class Role(Model, ObjectUtil.MagicClass):
    """角色表"""

    id        = fields.IntField(primary_key=True)
    role      = fields.CharEnumField(max_length=16, enum_type=EnumRole)
    role_desc = fields.CharField(max_length=32)
