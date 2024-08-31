#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import TypeVar

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from . import config
from .redis import redis_conn
from .exceptions import ForbiddenException, FailureException
from app.utils import DateTimeUtil
from app import schemas


T = TypeVar('T')

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='api/login')


def encrypt_password(password: str) -> str:
    """返回加密后的密码"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否正确"""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(data: dict):
    """创建访问令牌"""
    expire = DateTimeUtil.now() + config.ACCESS_TOKEN_EXPIRE_MINUTES
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    """创建刷新令牌"""
    expire = DateTimeUtil.now() + config.REFRESH_TOKEN_EXPIRE_MINUTES
    to_encode = data.copy()
    to_encode.update({'exp': expire, 'refresh_token': True})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """解析令牌为字典，若令牌无效将引发错误"""
    if redis_conn.get(token):
        raise ForbiddenException('令牌已销毁')

    return jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])


def revoke_token(token: str) -> bool:
    """将令牌放入黑名单"""
    redis_conn.set(token, 1, ex=config.ACCESS_TOKEN_EXPIRE_MINUTES)


def is_refresh_token(token: str) -> bool:
    """判断是否是刷新令牌"""
    payload = decode_token(token)

    return payload.get('refresh_token', False)


async def require_token(token: str = Depends(oauth2_scheme)) -> str:
    """返回令牌"""
    return token


async def require_refresh_token(token: str = Depends(require_token)) -> str:
    """返回刷新令牌"""
    if not is_refresh_token(token):
        raise FailureException('非刷新令牌')
    return token


async def get_current_user(token: str = Depends(require_token)) -> schemas.UserInToken:
    """获取 jwt 保存的用户信息"""
    payload = decode_token(token)
    current_user = schemas.UserInToken(**payload)

    if not current_user.is_active:
        raise ForbiddenException('账户已被禁用')

    return current_user


async def get_current_of_refresh(token: str = Depends(require_refresh_token)) -> schemas.UserInToken:
    """获取 jwt 保存的用户信息，并校验是否是刷新令牌"""
    payload = decode_token(token)
    current_user = schemas.UserInToken(**payload)

    if not current_user.is_active:
        raise ForbiddenException('账户已被禁用')

    return current_user
