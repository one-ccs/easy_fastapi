#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.append(__file__[:__file__.index('backend') + len('backend')])

from .logger import logger
from .exceptions import (
    TODOException,
    ForbiddenException,
    FailureException,
    UnauthorizedException,
    NotFoundException,
)
from . import config
from .generator import Generator
from .authorize import (
    TokenData,
    encrypt_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    revoke_token,
    require_token,
    require_refresh_token,
    get_current_user,
    get_current_refresh_user,
)
from .db import ExtendedCRUD, TORTOISE_ORM, init_tortoise, generate_schemas
from .redis import redis_conn
from .result import JSONResponseResult, Result


__all__ = [
    'logger',

    'TODOException',
    'ForbiddenException',
    'FailureException',
    'UnauthorizedException',
    'NotFoundException',

    'config',

    'Generator',

    'TokenData',
    'encrypt_password',
    'verify_password',
    'create_access_token',
    'create_refresh_token',
    'decode_token',
    'revoke_token',
    'require_token',
    'require_refresh_token',
    'get_current_user',
    'get_current_refresh_user',

    'ExtendedCRUD',
    'TORTOISE_ORM',
    'init_tortoise',
    'generate_schemas',

    'redis_conn',

    'JSONResponseResult',
    'Result',
]
