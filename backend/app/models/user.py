#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tortoise import Model, fields
from tortoise.expressions import Q
from easy_pyoc import ObjectUtil

from app.core import ExtendedCRUD
from .role import Role


class User(ObjectUtil.MagicClass, ExtendedCRUD, Model):
    """用户表"""
    _str_ignore = {'hashed_password'}

    id              = fields.IntField(primary_key=True, description='用户 id')
    email           = fields.CharField(max_length=64, null=True, unique=True, db_index=True, description='邮箱')
    username        = fields.CharField(max_length=32, null=True, unique=True, db_index=True, description='用户名')
    hashed_password = fields.CharField(max_length=64, description='密码')
    token           = fields.CharField(max_length=256, null=True, description='访问令牌')
    avatar_url      = fields.CharField(max_length=256, null=True, description='头像地址')
    is_active       = fields.BooleanField(default=True, description='是否激活')
    created_at      = fields.DatetimeField(auto_now_add=True, description='创建时间')

    roles: fields.ManyToManyRelation[Role] = fields.ManyToManyField(
        'models.Role', related_name='users', through='user_role',
    )

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
