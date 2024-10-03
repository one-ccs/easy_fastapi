#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tortoise import Tortoise

from . import config


TORTOISE_ORM = {
    'connections': {
        'default': config.DATABASE_URI,
    },
    'apps': {
        'models': {
            'models': ['aerich.models', 'app.models'],
            'default_connection': 'default',
        },
    },
}

async def init_tortoise():
    await Tortoise.init(config=TORTOISE_ORM)


async def generate_schemas():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()
