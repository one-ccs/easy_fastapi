#!/usr/bin/env python
# -*- coding: utf-8 -*-
from contextlib import asynccontextmanager

from fastapi import FastAPI
from easy_fastapi import EasyFastAPI, Config, init_tortoise
from easy_fastapi.authentication import EasyAuthentication

from .handlers.authentication import MyAuthHandler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动事件

    # 初始化数据库
    await init_tortoise()
    yield
    # 关闭事件
    pass


config = Config()

app = FastAPI(
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
easy_fastapi = EasyFastAPI(app)
auth = EasyAuthentication(app, authentication_handler=MyAuthHandler())
