#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import timedelta

from .yaml import read_yaml_config
from app.utils import PathUtil



ROOT_NAME = 'easy_fastapi'
CONFIG_FILE = 'backend/app/easy_fastapi.yaml'

_config = read_yaml_config(PathUtil.getProjectRoot(ROOT_NAME), CONFIG_FILE)


# Database
DATABASE_URL: str | None      = _config.get('easy_fastapi', {}).get('database', {}).get('url', None)
DATABASE_USER: str | None     = _config.get('easy_fastapi', {}).get('database', {}).get('username', None)
DATABASE_PASSWORD: str | None = _config.get('easy_fastapi', {}).get('database', {}).get('password', None)

# Authorization
SECRET_KEY: str | None        = _config.get('easy_fastapi', {}).get('authorization', {}).get('secret_key', None)
ALGORITHM: str                = _config.get('easy_fastapi', {}).get('authorization', {}).get('algorithm', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES   = _config.get('easy_fastapi', {}).get('authorization', {}).get('access_token_expire_minutes', 15)
REFRESH_TOKEN_EXPIRE_MINUTES  = _config.get('easy_fastapi', {}).get('authorization', {}).get('refresh_token_expire_minutes', 60 * 24 * 7)

# Redis
REDIS_HOST: str | None        = _config.get('easy_fastapi', {}).get('redis', {}).get('host', None)
REDIS_PORT: int               = _config.get('easy_fastapi', {}).get('redis', {}).get('port', 6379)
REDIS_PASSWORD: str | None    = _config.get('easy_fastapi', {}).get('redis', {}).get('password', None)
REDIS_DB: int                 = _config.get('easy_fastapi', {}).get('redis', {}).get('db', 0)
REDIS_DECODE_RESPONSES: bool  = _config.get('easy_fastapi', {}).get('redis', {}).get('decode_responses', True)


if not DATABASE_URL:
    raise ValueError(f'配置文件 "{CONFIG_FILE}" 缺少 "easy_fastapi.database.url" 配置')

if not DATABASE_USER:
    raise ValueError(f'配置文件 "{CONFIG_FILE}" 缺少 "easy_fastapi.database.username" 配置')

if not DATABASE_PASSWORD:
    raise ValueError(f'配置文件 "{CONFIG_FILE}" 缺少 "easy_fastapi.database.password" 配置')

if not SECRET_KEY:
    raise ValueError(f'配置文件 "{CONFIG_FILE}" 缺少 "easy_fastapi.authorization.SECRET_KEY" 配置')

if not REDIS_HOST:
    raise ValueError(f'配置文件 "{CONFIG_FILE}" 缺少 "easy_fastapi.redis.host" 配置')


DATABASE_URI: str = DATABASE_URL.replace('://', f'://{DATABASE_USER}:{DATABASE_PASSWORD}@')

ACCESS_TOKEN_EXPIRE_MINUTES : timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
REFRESH_TOKEN_EXPIRE_MINUTES: timedelta = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
