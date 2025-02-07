#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class Token(BaseModel):
    """由 JWT 解析的 Token 数据类"""

    # 是否是刷新令牌
    isr: bool = False
    # 权限列表
    sco: list[str] | None = None
    # 用户名
    sub: str
    # 过期时间
    exp: datetime
    # 发行者
    iss: str | None = None
    # 接收者
    aud: str | None = None
    # 签发时间
    iat: datetime | None = None
    # 生效时间
    nbf: datetime | None = None
    # JWT 唯一标识
    jti: str | None = None

    def has_permission(self, scopes: Optional[list[str]] = None) -> bool:
        """检查是否有指定权限"""
        if scopes is None or scopes == []:
            return True
        if self.sco is None or self.sco == []:
            return False
        return not set(self.sco).isdisjoint(set(scopes))


class BaseUser(BaseModel):
    """基础用户信息"""

    username: str
    scopes: list[str]


class APIToken(BaseModel):
    token_type: str
    access_token: str
    refresh_token: str


class APIRefresh(BaseModel):
    token_type: str
    access_token: str


class APILogin(BaseModel):
    user: BaseUser
    token_type: str
    access_token: str
    refresh_token: str
