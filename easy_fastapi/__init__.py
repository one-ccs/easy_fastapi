#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .generator import Generator as Generator
from .logger import uvicorn_logger as uvicorn_logger
from .exceptions import (
    TODOException as TODOException,
    FailureException as FailureException,
    UnauthorizedException as UnauthorizedException,
    ForbiddenException as ForbiddenException,
    NotFoundException as NotFoundException,
)
from .authorize import (
    TokenData as TokenData,
    encrypt_password as encrypt_password,
    verify_password as verify_password,
    create_access_token as create_access_token,
    create_refresh_token as create_refresh_token,
    decode_token as decode_token,
    revoke_token as revoke_token,
    require_token as require_token,
    require_refresh_token as require_refresh_token,
    require_permission as require_permission,
    get_current_user as get_current_user,
    get_current_refresh_user as get_current_refresh_user,
)
from .config import (
    CONFIG_PATH as CONFIG_PATH,
    Config as Config,
    config as config,
)
from .db import (
    TORTOISE_ORM as TORTOISE_ORM,
    init_tortoise as init_tortoise,
    generate_schemas as generate_schemas,
    Pagination as Pagination,
    ExtendedCRUD as ExtendedCRUD,
)
from .result import (
    Result as Result,
    JSONResponseResult as JSONResponseResult,
)

from easy_pyoc import PackageUtil


__version__ = PackageUtil.get_version('easy_fastapi')
__author__  = 'one-ccs'
__email__   = 'one-ccs@foxmal.com'

__all__ = [
    'Generator',

    'uvicorn_logger',

    'TODOException',
    'FailureException',
    'UnauthorizedException',
    'ForbiddenException',
    'NotFoundException',

    'TokenData',
    'encrypt_password',
    'verify_password',
    'create_access_token',
    'create_refresh_token',
    'decode_token',
    'revoke_token',
    'require_token',
    'require_refresh_token',
    'require_permission',
    'get_current_user',
    'get_current_refresh_user',

    'CONFIG_PATH',
    'Config',
    'config',

    'TORTOISE_ORM',
    'init_tortoise',
    'generate_schemas',
    'Pagination',
    'ExtendedCRUD',

    'Result',
    'JSONResponseResult',
]
