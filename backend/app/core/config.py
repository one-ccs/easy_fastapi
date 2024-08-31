#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .yaml import read_config
from app.utils import PathUtil


ROOT_NAME = 'easy_fastapi'
CONFIG_FILE = 'backend/app/easy_fastapi.yaml'

_config = read_config(PathUtil.getProjectRoot(ROOT_NAME), CONFIG_FILE)

# Database
DATABASE_URL                 = _config.get('easy_fastapi', {}).get('database', {}).get('url', None)
DATABASE_USER                = _config.get('easy_fastapi', {}).get('database', {}).get('username', None)
DATABASE_PASSWORD            = _config.get('easy_fastapi', {}).get('database', {}).get('password', None)

# Authorization
SECRET_KEY                   = _config.get('easy_fastapi', {}).get('authorization', {}).get('secret_key', None)
ALGORITHM                    = _config.get('easy_fastapi', {}).get('authorization', {}).get('algorithm', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES  = _config.get('easy_fastapi', {}).get('authorization', {}).get('access_token_expire_minutes', 15)
REFRESH_TOKEN_EXPIRE_MINUTES = _config.get('easy_fastapi', {}).get('authorization', {}).get('refresh_token_expire_minutes', 60 * 24 * 7)

if not DATABASE_URL:
    raise ValueError(f'配置文件 "{CONFIG_FILE}" 缺少 "easy_fastapi.database.url" 配置')

if not DATABASE_USER:
    raise ValueError(f'配置文件 "{CONFIG_FILE}" 缺少 "easy_fastapi.database.username" 配置')

if not DATABASE_PASSWORD:
    raise ValueError(f'配置文件 "{CONFIG_FILE}" 缺少 "easy_fastapi.database.password" 配置')

if not SECRET_KEY:
    raise ValueError(f'配置文件 "{CONFIG_FILE}" 缺少 "easy_fastapi.authorization.SECRET_KEY" 配置')

# 数据库完整连接
DATABASE_URI = DATABASE_URL.replace('://', f'://{DATABASE_USER}:{DATABASE_PASSWORD}@')
