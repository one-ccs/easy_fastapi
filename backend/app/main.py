#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core import logger, config, init_tortoise


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动事件

    # 初始化数据库
    await init_tortoise()
    yield
    # 关闭事件
    pass


app = FastAPI(
    root_path=config.ROOT_PATH,
    docs_url=config.SWAGGER_DOCS_URL,
    redoc_url=config.SWAGGER_REDOC_URL,
    openapi_url=config.SWAGGER_OPENAPI_URL,
    title='Easy FastAPI',
    description='基于 FastAPI 开发的后端框架，集成了 Tortoise ORM、Pydantic、Aerich、PyJWT、PyYAML、Redis 等插件，旨在提供一个高效、易用的后端开发环境。该框架通过清晰的目录结构和模块化设计，帮助开发者快速构建和部署后端服务。',
    version='1.8.0',
    contact={
        'name': 'one-ccs@foxmail.com',
        'email': 'one-ccs@foxmail.com',
    },
    license_info={
        'name': '开源协议：MIT',
        'url': 'https://github.com/one-ccs/easy_fastapi?tab=MIT-1-ov-file#readme',
    },
    lifespan=lifespan,
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

if config.TEMPLATES_FOLDER:
    logger.debug(f'静态文件配置: {config.TEMPLATES_FOLDER}')
    with open(config.TEMPLATES_FOLDER + '/index.html', 'r', encoding='utf-8') as f:
        index_html = f.read()

    @app.get('/', response_class=HTMLResponse)
    async def root():
        return index_html

if config.STATIC_NAME and config.STATIC_URL and config.STATIC_FOLDER:
    logger.debug(f'静态资源配置: {config.STATIC_NAME} -> {config.STATIC_URL} -> {config.STATIC_FOLDER}')
    app.mount(config.STATIC_URL, StaticFiles(directory=config.STATIC_FOLDER), name=config.STATIC_NAME)


@app.middleware('http')
async def response_status_code_middleware(request: Request, call_next: Callable[[Request], Response]) -> Response:
    response: Response = await call_next(request)

    if config.FORCE_200_CODE:
        response.status_code = 200

    return response
