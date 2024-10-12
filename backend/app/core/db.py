#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Type, TypeVar, Generic, Any
from dataclasses import dataclass

from tortoise import Tortoise, Model
from tortoise.expressions import Q

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
    """扩展 CRUD"""

    @dataclass
    class Pagination(Generic[_TModel]):
        total: int
        items: list[_TModel]
        finished: bool

    @classmethod
    async def by_id(cls: Type[_TModel], id: int) -> _TModel | None:
        return await cls.get_or_none(id=id)

    @classmethod
    async def paginate(cls: Type[_TModel], page_index: int, page_size: int, *args: Q, **kwargs: Any) -> Pagination[_TModel]:
        base_filter = cls.filter(*args, **kwargs)
        total = await base_filter.count()
        items = await base_filter.limit(page_size).offset((page_index - 1) * page_size)
        finished = total <= page_size * page_index

        return ExtendedCRUD.Pagination(total=total, items=items, finished=finished)
