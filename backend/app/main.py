#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core import config


app = FastAPI(
    title='Easy FastAPI',
    description='基于 FastAPI 开发的后端框架，集成了 SQLAlchemy、Pydantic、Alembic、PyJWT、PyYAML、Redis 等插件，旨在提供一个高效、易用的后端开发环境。该框架通过清晰的目录结构和模块化设计，帮助开发者快速构建和部署后端服务。',
    version='1.3.0',
    contact={
        'name': 'one-ccs@foxmail.com',
        'email': 'one-ccs@foxmail.com',
    },
    license_info={
        'name': '开源协议：MIT',
        'url': 'https://github.com/one-ccs/easy_fastapi?tab=MIT-1-ov-file#readme',
    },
)

if config.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ALLOW_ORIGINS,
        allow_credentials=config.CORS_ALLOW_CREDENTIALS,
        allow_methods=config.CORS_ALLOW_METHODS,
        allow_headers=config.CORS_ALLOW_HEADERS,
    )

if config.HTTPS_REDIRECT_ENABLED:
    app.add_middleware(HTTPSRedirectMiddleware)

if config.TRUSTED_HOST_ENABLED:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=config.TRUSTED_HOST_ALLOWED_HOSTS
    )

if config.GZIP_ENABLED:
    app.add_middleware(
        GZipMiddleware,
        minimum_size=config.GZIP_MINIMUM_SIZE,
        compresslevel=config.GZIP_COMPRESS_LEVEL
    )


@app.middleware('http')
async def response_status_code_middleware(request: Request, call_next) -> Response:
    response: Response = await call_next(request)

    if config.FORCE_200_CODE:
        response.status_code = 200

    return response
