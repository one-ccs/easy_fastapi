#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import TypeVar, Callable
from datetime import datetime
from inspect import iscoroutinefunction

import bcrypt
from jwt import (
    encode as encode_jwt,
    decode as decode_jwt,
)
from easy_pyoc import DateTimeUtil

from ..config import Config
from .schemas import Token


T = TypeVar('T')


async def _async(func: Callable[..., T], *args, **kwargs) -> T:
    """以异步方式调用同步函数"""
    if iscoroutinefunction(func):
        return await func(*args, **kwargs)
    return func(*args, **kwargs)


async def encrypt_password(password: str) -> str:
    """返回加密后的密码

    Args:
        password (str): 明文密码

    Returns:
        str: 加密后的密码
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否正确

    Args:
        plain_password (str): 明文密码
        hashed_password (str): 加密后的密码

    Returns:
        bool: 密码是否正确
    """
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


async def create_access_token(
    *,
    sub: str,
    sco: list[str] | None = None,
    iat: datetime = DateTimeUtil.now(),
) -> str:
    """创建访问令牌

    Args:
        sub (str): 用户名
        sco (list[str], optional): 权限列表. 默认为 None.
        iss (str, optional): 发行者. 默认为 None.
        iat (datetime, optional): 签发时间. 默认为 DateTimeUtil.now().

    Returns:
        str: 访问令牌
    """
    config = Config()

    expire = DateTimeUtil.now() + config.easy_fastapi.authentication.access_token_expire_minutes
    iss = config.easy_fastapi.authentication.iss
    to_encode = {'sub': sub, 'sco': sco, 'exp': expire, 'iss': iss, 'iat': iat, 'isr': False}
    encoded_jwt = encode_jwt(
        to_encode,
        config.easy_fastapi.authentication.secret_key,
        config.easy_fastapi.authentication.algorithm,
    )
    return encoded_jwt


async def create_refresh_token(
    *,
    sub: str,
    sco: list[str] | None = None,
    iat: datetime = DateTimeUtil.now(),
) -> str:
    """创建刷新令牌

    Args:
        sub (str): 用户名
        sco (list[str], optional): 权限列表. 默认为 None.
        iat (datetime, optional): 签发时间. 默认为 DateTimeUtil.now().

    Returns:
        str: 刷新令牌
    """
    config = Config()

    expire = DateTimeUtil.now() + config.easy_fastapi.authentication.refresh_token_expire_minutes
    iss = config.easy_fastapi.authentication.iss
    to_encode = {'sub': sub, 'sco': sco, 'exp': expire, 'iss': iss, 'iat': iat, 'isr': True}
    encoded_jwt = encode_jwt(
        to_encode,
        config.easy_fastapi.authentication.secret_key,
        config.easy_fastapi.authentication.algorithm,
    )
    return encoded_jwt


async def decode_token(jwt: str) -> Token:
    """解析 JWT 令牌为字典，若令牌无效将引发错误

    Args:
        jwt (str): JWT 令牌

    Returns:
        Token: 令牌数据
    """
    config = Config()

    payload = decode_jwt(
        jwt,
        config.easy_fastapi.authentication.secret_key,
        algorithms=[
            config.easy_fastapi.authentication.algorithm,
        ],
    )

    return Token(**payload)
