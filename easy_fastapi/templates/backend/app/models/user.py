#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tortoise import Model, fields
from tortoise.expressions import Q
from easy_pyoc import Magic

from easy_fastapi import ExtendedCRUD
from easy_fastapi.authentication import UserMixin
from .role import Role


class User(Magic, UserMixin, ExtendedCRUD, Model):
    """用户表"""
    _str_exclude = {'hashed_password'}
    _str_include = {'_roles'}

    id              = fields.IntField(primary_key=True, description='用户 id')
    email           = fields.CharField(max_length=64, null=True, unique=True, db_index=True, description='邮箱')
    username        = fields.CharField(max_length=32, null=True, unique=True, db_index=True, description='用户名')
    hashed_password = fields.CharField(max_length=64, description='密码')
    token           = fields.CharField(max_length=255, null=True, description='访问令牌')
    avatar_url      = fields.CharField(max_length=255, null=True, description='头像地址')
    is_active       = fields.BooleanField(default=True, description='是否激活')
    created_at      = fields.DatetimeField(auto_now_add=True, description='创建时间')

    roles: fields.ManyToManyRelation[Role] = fields.ManyToManyField(
        'models.Role', related_name='users', through='user_role', description='用户角色',
    )

    @property
    def identity(self) -> str:
        return self.username or self.email

    @property
    def h_pwd(self) -> str:
        return self.hashed_password

    @property
    def scopes(self) -> list[str]:
        """获取用户权限"""
        return [role.role for role in self.roles]

    @staticmethod
    async def by_username(username: str):
        return await User.filter(username=username).prefetch_related('roles').first()

    @staticmethod
    async def by_email(email: str):
        return await User.filter(email=email).prefetch_related('roles').first()

    @staticmethod
    async def by_username_or_email(username_or_email: str):
        return await User.filter(
            Q(username=username_or_email) | Q(email=username_or_email),
        ).prefetch_related('roles').first()
