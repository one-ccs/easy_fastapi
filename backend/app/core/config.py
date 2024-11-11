#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Any
from pathlib import Path
from datetime import timedelta
from easy_pyoc import ObjectUtil, PathUtil

from .logger import logger
from .yaml import read_yaml


CONFIG_PATH = Path(__file__).parent.parent.joinpath('easy_fastapi.yaml')

if not PathUtil.is_exists_file(CONFIG_PATH):
    raise FileNotFoundError(f'配置文件 {CONFIG_PATH} 不存在')

yaml_config = read_yaml(CONFIG_PATH) or {}


def get_config(path: str, default: Any = None) -> Any:
    """获取配置内容

    Args:
        path (str): 配置路径，以点号分隔，如 "easy_fastapi.app.force_200_code"
        default (Any, optional): 默认值. Defaults to None.

    Returns:
        Any: 配置内容
    """
    return ObjectUtil.get_value_from_dict(yaml_config, path, default)


# easy_fastapi
FORCE_200_CODE: bool            = get_config('easy_fastapi.force_200_code', False)

SECRET_KEY: str | None          = get_config('easy_fastapi.authorization.secret_key', None)
ALGORITHM: str                  = get_config('easy_fastapi.authorization.algorithm', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES     = get_config('easy_fastapi.authorization.access_token_expire_minutes', 15)
REFRESH_TOKEN_EXPIRE_MINUTES    = get_config('easy_fastapi.authorization.refresh_token_expire_minutes', 60 * 24 * 7)

UPLOAD_FOLDER: str | None       = get_config('easy_fastapi.resources.upload_folder', None)
TEMPLATES_FOLDER: str | None    = get_config('easy_fastapi.resources.templates_folder', None)
STATIC_NAME: str | None         = get_config('easy_fastapi.resources.static.name', None)
STATIC_URL: str | None          = get_config('easy_fastapi.resources.static.url', None)
STATIC_FOLDER: str | None       = get_config('easy_fastapi.resources.static.folder', None)

# fastapi
ROOT_PATH: str                  = get_config('fastapi.root_path', '/api')

SWAGGER_TOKEN_URL: str          = get_config('fastapi.swagger.token_url', '/token')
SWAGGER_DOCS_URL: str           = get_config('fastapi.swagger.docs_url', '/docs')
SWAGGER_REDOC_URL: str          = get_config('fastapi.swagger.redoc_url', '/redoc')
SWAGGER_OPENAPI_URL: str        = get_config('fastapi.swagger.openapi_url', '/openapi.json')

CORS_ENABLED: bool              = get_config('fastapi.cors.cors_enabled', False)
CORS_ALLOW_ORIGINS: list[str]   = get_config('fastapi.cors.cors_allow_origins', ['*'])
CORS_ALLOW_CREDENTIALS: bool    = get_config('fastapi.cors.cors_allow_credentials', True)
CORS_ALLOW_METHODS: list[str]   = get_config('fastapi.cors.cors_allow_methods', ['*'])
CORS_ALLOW_HEADERS: list[str]   = get_config('fastapi.cors.cors_allow_headers', ['*'])

HTTPS_REDIRECT_ENABLED: bool    = get_config('fastapi.middleware.https_redirect.enabled', False)
TRUSTED_HOST_ENABLED: bool      = get_config('fastapi.middleware.trusted_host.enabled', False)
TRUSTED_HOST_ALLOWED_HOSTS: list[str] = get_config('fastapi.middleware.trusted_host.allowed_hosts', ['*'])
GZIP_ENABLED: bool              = get_config('fastapi.middleware.gzip.enabled', False)
GZIP_MINIMUM_SIZE: int          = get_config('fastapi.middleware.gzip.minimum_size', 1000)
GZIP_COMPRESS_LEVEL: int        = get_config('fastapi.middleware.gzip.compresslevel', 5)

# database
DATABASE_URL: str | None        = get_config('database.url', None)
DATABASE_USER: str | None       = get_config('database.username', None)
DATABASE_PASSWORD: str | None   = get_config('database.password', None)
DATABASE_ECHO: bool             = get_config('database.echo', False)
DATABASE_TIMEZONE: str          = get_config('database.timezone', 'Asia/Chongqing')

# redis
REDIS_HOST: str | None          = get_config('redis.host', None)
REDIS_PORT: int                 = get_config('redis.port', 6379)
REDIS_PASSWORD: str | None      = get_config('redis.password', None)
REDIS_DB: int                   = get_config('redis.db', 0)
REDIS_DECODE_RESPONSES: bool    = get_config('redis.decode_responses', True)


if not DATABASE_URL:
    raise ValueError(f'配置文件 "{CONFIG_PATH}" 缺少 "database.url" 配置')

if not DATABASE_USER:
    raise ValueError(f'配置文件 "{CONFIG_PATH}" 缺少 "database.username" 配置')

if not DATABASE_PASSWORD:
    raise ValueError(f'配置文件 "{CONFIG_PATH}" 缺少 "database.password" 配置')

if not SECRET_KEY:
    raise ValueError(f'配置文件 "{CONFIG_PATH}" 缺少 "authorization.SECRET_KEY" 配置')

if not REDIS_HOST:
    raise ValueError(f'配置文件 "{CONFIG_PATH}" 缺少 "easy_fastapi.redis.host" 配置')

if SECRET_KEY in ('easy_fastapi', '123456', 'pass'):
    logger.warning(f'配置文件 "{CONFIG_PATH}" 设置项 "easy_fastapi.authorization.secret_key={SECRET_KEY}" 不安全，请修改为更安全的秘钥。')


DATABASE_URI: str = DATABASE_URL.replace('://', f'://{DATABASE_USER}:{DATABASE_PASSWORD}@')

ACCESS_TOKEN_EXPIRE_MINUTES : timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
REFRESH_TOKEN_EXPIRE_MINUTES: timedelta = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)


if UPLOAD_FOLDER:
    UPLOAD_FOLDER = PathUtil.abspath(UPLOAD_FOLDER)

if TEMPLATES_FOLDER:
    TEMPLATES_FOLDER = PathUtil.abspath(TEMPLATES_FOLDER)

if STATIC_FOLDER:
    STATIC_FOLDER = PathUtil.abspath(STATIC_FOLDER)
