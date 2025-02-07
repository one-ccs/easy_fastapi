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
    JSONResult as JSONResult,
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
    'JSONResult',

    'Generator',
]
