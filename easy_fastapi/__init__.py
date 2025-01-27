#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .easy_fastapi import EasyFastAPI as EasyFastAPI
from .logger import uvicorn_logger as uvicorn_logger
from .exception import (
    TODOException as TODOException,
    FailureException as FailureException,
    UnauthorizedException as UnauthorizedException,
    ForbiddenException as ForbiddenException,
    NotFoundException as NotFoundException,
)
from .authorize import (
    AUTH_HEADER_NAME as AUTH_HEADER_NAME,
    AUTH_TYPE as AUTH_TYPE,
    Token as Token,
    TokenUser as TokenUser,
    UserMixin as UserMixin,
    EasyFastAPIAuthorize as EasyFastAPIAuthorize,
    encrypt_password as encrypt_password,
    verify_password as verify_password,
    create_access_token as create_access_token,
    create_refresh_token as create_refresh_token,
    decode_token as decode_token,
)
from .db import (
    init_tortoise as init_tortoise,
    generate_schemas as generate_schemas,
    Pagination as Pagination,
    ExtendedCRUD as ExtendedCRUD,
)
from .config import (
    CONFIG_PATH as CONFIG_PATH,
    Config as Config,
)
from .persistence import (
    BasePersistence as BasePersistence,
    Persistence as Persistence,
)
from .result import (
    Result as Result,
    JSONResponseResult as JSONResponseResult,
)
from .generator import Generator as Generator

from easy_pyoc import PackageUtil


__version__ = PackageUtil.get_version('easy_fastapi')
__author__  = 'one-ccs'
__email__   = 'one-ccs@foxmal.com'

__all__ = [
    'EasyFastAPI',

    'uvicorn_logger',

    'TODOException',
    'FailureException',
    'UnauthorizedException',
    'ForbiddenException',
    'NotFoundException',

    'AUTH_HEADER_NAME',
    'AUTH_TYPE',
    'Token',
    'TokenUser',
    'UserMixin',
    'EasyFastAPIAuthorize',
    'encrypt_password',
    'verify_password',
    'create_access_token',
    'create_refresh_token',
    'decode_token',

    'init_tortoise',
    'generate_schemas',
    'Pagination',
    'ExtendedCRUD',

    'CONFIG_PATH',
    'Config',

    'BasePersistence',
    'Persistence',

    'Result',
    'JSONResponseResult',

    'Generator',
]
