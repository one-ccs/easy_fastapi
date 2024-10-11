#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from easy_pyoc import DateTimeUtil

from . import config
from .redis import redis_conn
from .exceptions import ForbiddenException


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=config.SWAGGER_TOKEN_URL)


class TokenData(BaseModel):
    # 是否是刷新令牌
    isr: bool
    # 权限集合
    sco: set[str] | None = None
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
    # 唯一标识
    jti: str | None = None


def encrypt_password(password: str) -> str:
    """返回加密后的密码"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否正确"""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(*, sub: str) -> str:
    """创建访问令牌"""
    expire = DateTimeUtil.now() + config.ACCESS_TOKEN_EXPIRE_MINUTES
    to_encode = {'sub': sub, 'exp': expire, 'isr': False}
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt


def create_refresh_token(*, sub: str) -> str:
    """创建刷新令牌"""
    expire = DateTimeUtil.now() + config.REFRESH_TOKEN_EXPIRE_MINUTES
    to_encode = {'sub': sub, 'exp': expire, 'isr': True}
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """解析令牌为字典，若令牌无效将引发错误"""
    if redis_conn.get(token):
        raise ForbiddenException('令牌已销毁')

    payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])

    return TokenData(**payload)


def revoke_token(token: str) -> bool:
    """将令牌放入黑名单"""
    redis_conn.set(token, 1, ex=config.ACCESS_TOKEN_EXPIRE_MINUTES)


async def require_token(token: str = Depends(oauth2_scheme)) -> str:
    """返回令牌"""
    return token


async def require_refresh_token(token: str = Depends(require_token)) -> str:
    """返回刷新令牌"""
    payload = decode_token(token)

    if not payload.isr:
        raise ForbiddenException('需要刷新令牌')

    return token


async def require_permission(permissions: set[str], token: str = Depends(require_token)) -> TokenData:
    """检查用户是否具有指定的所有权限"""
    payload = decode_token(token)

    if not payload.sco or not payload.sco.issuperset(permissions):
        raise ForbiddenException('无权访问')
    return payload


async def get_current_user(token: str = Depends(require_token)) -> TokenData:
    """返回当前用户"""
    return decode_token(token)


async def get_current_refresh_user(token: str = Depends(require_refresh_token)) -> TokenData:
    """返回当前用户（从刷新令牌解析）"""
    return decode_token(token)
