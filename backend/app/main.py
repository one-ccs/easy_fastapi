#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
