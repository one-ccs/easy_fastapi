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

from easy_fastapi import uvicorn_logger, config, init_tortoise


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动事件

    # 初始化数据库
    await init_tortoise()
    yield
    # 关闭事件
    pass


app = FastAPI(
    root_path=config.fastapi.root_path,
    docs_url=config.fastapi.swagger.docs_url,
    redoc_url=config.fastapi.swagger.redoc_url,
    openapi_url=config.fastapi.swagger.openapi_url,
    title=config.fastapi.swagger.title,
    description=config.fastapi.swagger.description,
    version=config.fastapi.swagger.version,
    contact={
        'name': config.fastapi.swagger.contact.name,
        'url': config.fastapi.swagger.contact.url,
        'email': config.fastapi.swagger.contact.email,
    },
    license_info={
        'name': config.fastapi.swagger.license.name,
        'url': config.fastapi.swagger.license.url,
    },
    lifespan=lifespan,
)

if config.fastapi.middleware.cors.enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=config.fastapi.middleware.cors.allow_origin_regex,
        allow_origins=config.fastapi.middleware.cors.allow_origins,
        allow_methods=config.fastapi.middleware.cors.allow_methods,
        allow_headers=config.fastapi.middleware.cors.allow_headers,
        allow_credentials=config.fastapi.middleware.cors.allow_credentials,
        expose_headers=config.fastapi.middleware.cors.expose_headers,
        max_age=config.fastapi.middleware.cors.max_age,
    )

if config.fastapi.middleware.https_redirect.enabled:
    app.add_middleware(HTTPSRedirectMiddleware)

if config.fastapi.middleware.trusted_host.enabled:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=config.fastapi.middleware.trusted_host.allowed_hosts,
    )

if config.fastapi.middleware.gzip.enabled:
    app.add_middleware(
        GZipMiddleware,
        minimum_size=config.fastapi.middleware.gzip.minimum_size,
        compresslevel=config.fastapi.middleware.gzip.compress_level,
    )

if config.easy_fastapi.resources.is_template:
    templates_folder = config.easy_fastapi.resources.templates_folder

    uvicorn_logger.debug(f'静态文件配置: {templates_folder}')
    with open(templates_folder + '/index.html', 'r', encoding='utf-8') as f:
        index_html = f.read()

    @app.get('/', response_class=HTMLResponse)
    async def root():
        return index_html

if config.easy_fastapi.resources.is_static:
    static_folder = config.easy_fastapi.resources.static_folder
    static_name = config.easy_fastapi.resources.static_name
    static_url = config.easy_fastapi.resources.static_url

    uvicorn_logger.debug(f'静态资源配置: {static_url} -> {static_folder}/{static_name}')
    app.mount(static_url, StaticFiles(directory=static_folder), name=static_name)


@app.middleware('http')
async def response_status_code_middleware(request: Request, call_next: Callable[[Request], Response]) -> Response:
    response: Response = await call_next(request)

    if config.easy_fastapi.force_success_code:
        response.status_code = 200

    return response
