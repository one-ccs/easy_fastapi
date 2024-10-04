#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tortoise import Model, fields
from tortoise.expressions import Q

from app.core import ExtendedCRUD
from app.utils import ObjectUtil


class User(Model, ExtendedCRUD, ObjectUtil.MagicClass):
    """用户表"""

    id              = fields.IntField(primary_key=True)
    email           = fields.CharField(max_length=64, null=True, unique=True, db_index=True)
    username        = fields.CharField(max_length=32, null=True, unique=True, db_index=True)
    hashed_password = fields.CharField(max_length=64)
    token           = fields.CharField(max_length=255, null=True)
    avatar_url      = fields.CharField(max_length=256, null=True)
    is_active       = fields.BooleanField(default=True)
    created_at      = fields.DatetimeField(auto_now_add=True)

    roles           = fields.ManyToManyField('models.Role', related_name='users')

    @staticmethod
    async def by_username(username: str):
        return await User.filter(username=username).first()

    @staticmethod
    async def by_email(email: str):
        return await User.filter(email=email).first()

    @staticmethod
    async def by_username_or_email(username_or_email: str):
        return await User.filter(
            Q(username=username_or_email) | Q(email=username_or_email),
        ).first()

    async def get_roles(self):
        return await self.roles.all()
