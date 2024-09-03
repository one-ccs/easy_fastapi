#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Any
from pathlib import Path
from datetime import timedelta

from .yaml import read_yaml_config
from app.utils import ObjectUtil, PathUtil


CONFIG_PATH = Path(__file__).parent.parent.joinpath('easy_fastapi.yaml')

yaml_config = read_yaml_config(CONFIG_PATH) or {}


def get_config(path: str, default: Any = None) -> Any:
    """获取配置内容

    Args:
        path (str): 配置路径，以点号分隔，如 "easy_fastapi.app.force_200_code"
        default (Any, optional): 默认值. Defaults to None.

    Returns:
        Any: 配置内容
    """
    return ObjectUtil.get_value_from_dict(yaml_config, path, default)


# App
FORCE_200_CODE: bool          = get_config('easy_fastapi.app.force_200_code', False)

# Database
DATABASE_URL: str | None      = get_config('easy_fastapi.database.url', None)
DATABASE_USER: str | None     = get_config('easy_fastapi.database.username', None)
DATABASE_PASSWORD: str | None = get_config('easy_fastapi.database.password', None)

# Redis
REDIS_HOST: str | None        = get_config('easy_fastapi.redis.host', None)
REDIS_PORT: int               = get_config('easy_fastapi.redis.port', 6379)
REDIS_PASSWORD: str | None    = get_config('easy_fastapi.redis.password', None)
REDIS_DB: int                 = get_config('easy_fastapi.redis.db', 0)
REDIS_DECODE_RESPONSES: bool  = get_config('easy_fastapi.redis.decode_responses', True)

# Authorization
SECRET_KEY: str | None        = get_config('easy_fastapi.authorization.secret_key', None)
ALGORITHM: str                = get_config('easy_fastapi.authorization.algorithm', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES   = get_config('easy_fastapi.authorization.access_token_expire_minutes', 15)
REFRESH_TOKEN_EXPIRE_MINUTES  = get_config('easy_fastapi.authorization.refresh_token_expire_minutes', 60 * 24 * 7)

# Resources
UPLOAD_FOLDER                 = get_config('easy_fastapi.resources.upload_folder', None)
TEMPLATES_FOLDER              = get_config('easy_fastapi.resources.templates_folder', None)
STATIC_FOLDER                 = get_config('easy_fastapi.resources.static_folder', None)


if not DATABASE_URL:
    raise ValueError(f'配置文件 "{CONFIG_PATH}" 缺少 "easy_fastapi.database.url" 配置')

if not DATABASE_USER:
    raise ValueError(f'配置文件 "{CONFIG_PATH}" 缺少 "easy_fastapi.database.username" 配置')

if not DATABASE_PASSWORD:
    raise ValueError(f'配置文件 "{CONFIG_PATH}" 缺少 "easy_fastapi.database.password" 配置')

if not SECRET_KEY:
    raise ValueError(f'配置文件 "{CONFIG_PATH}" 缺少 "easy_fastapi.authorization.SECRET_KEY" 配置')

if not REDIS_HOST:
    raise ValueError(f'配置文件 "{CONFIG_PATH}" 缺少 "easy_fastapi.redis.host" 配置')


DATABASE_URI: str = DATABASE_URL.replace('://', f'://{DATABASE_USER}:{DATABASE_PASSWORD}@')

ACCESS_TOKEN_EXPIRE_MINUTES : timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
REFRESH_TOKEN_EXPIRE_MINUTES: timedelta = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)

UPLOAD_FOLDER: str    = PathUtil.abspath(UPLOAD_FOLDER)
TEMPLATES_FOLDER: str = PathUtil.abspath(TEMPLATES_FOLDER)
STATIC_FOLDER: str    = PathUtil.abspath(STATIC_FOLDER)
