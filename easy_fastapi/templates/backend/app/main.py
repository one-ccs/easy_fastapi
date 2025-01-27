#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import FastAPI
from easy_fastapi import EasyFastAPI, Config


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
)
easy_fastapi = EasyFastAPI(app)
