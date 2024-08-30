#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title='Easy FastAPI',
    description='基于 FastAPI 开发的后端框架，集成 SQLAlchemy、Pydantic、Alembic、PyJWT 等插件。',
    version='0.0.1',
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
