#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Type, TypeVar

from tortoise import Tortoise, Model

from . import config


_TModel = TypeVar('_TModel', bound=Model)

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


class ExtendedCRUD():

    @classmethod
    async def by_id(cls: Type[_TModel], id: int) -> _TModel | None:
        return await cls.get_or_none(id=id)

    @classmethod
    async def page(cls: Type[_TModel], page: int, page_size: int):
        return await cls.all().limit(page_size).offset((page - 1) * page_size)
