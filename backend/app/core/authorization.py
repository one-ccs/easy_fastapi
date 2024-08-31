#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import TypeVar
from datetime import timedelta, datetime, timezone

import jwt
import bcrypt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core import UnauthorizedException, ForbiddenException, config


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='api/login')
T = TypeVar('T')


def encrypt_password(password: str) -> str:
    """返回加密后的密码"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否正确"""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(data: dict):
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=config.REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({'exp': expire, 'refresh_token': True})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException('访问令牌已过期')
    except jwt.InvalidTokenError:
        raise UnauthorizedException('无效的访问令牌')


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    return decode_token(token)


async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    if not current_user.get('is_active', True):
        raise ForbiddenException('账户已被禁用')
    return current_user
