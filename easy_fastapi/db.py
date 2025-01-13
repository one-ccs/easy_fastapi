#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from typing import Type, TypeVar, Generic, Any
from dataclasses import dataclass

from tortoise import Tortoise, Model
from tortoise.expressions import Q
from tortoise.query_utils import Prefetch

from .config import config


_TModel = TypeVar('_TModel', bound=Model)


TORTOISE_ORM = {
    'connections': {
        'default': config.database.uri,
    },
    'apps': {
        'models': {
            'models': ['aerich.models', 'app.models'],
            'default_connection': 'default',
        },
    },
    'use_tz': False,
    'timezone': config.database.timezone,
}


async def init_tortoise():
    if config.database.echo:
        # 配置日志记录器
        logger = logging.getLogger('tortoise')
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        logger.addHandler(handler)

    await Tortoise.init(config=TORTOISE_ORM)


async def generate_schemas():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()


@dataclass
class Pagination(Generic[_TModel]):
    total: int
    items: list[_TModel]
    finished: bool


class ExtendedCRUD():
    """扩展 CRUD"""

    @classmethod
    async def by_id(cls: Type[_TModel], id: int, prefetch: tuple[str | Prefetch] | None = None) -> _TModel | None:
        if prefetch and not isinstance(prefetch, tuple):
            raise TypeError('prefetch 参数应该是 tuple[str | Prefetch] 类型')

        return await cls.get_or_none(id=id).prefetch_related(*prefetch) if prefetch else await cls.get_or_none(id=id)

    @classmethod
    async def paginate(cls: Type[_TModel], page_index: int, page_size: int, prefetch: tuple[str | Prefetch] | None = None, *args: Q, **kwargs: Any) -> Pagination[_TModel]:
        if prefetch and not isinstance(prefetch, tuple):
            raise TypeError('prefetch 参数应该是 tuple[str | Prefetch] 类型')

        base_filter = cls.filter(*args, **kwargs).prefetch_related(*prefetch) if prefetch else cls.filter(*args, **kwargs)
        total = await base_filter.count()
        items = await base_filter.limit(page_size).offset((page_index - 1) * page_size)
        finished = total <= page_size * page_index

        return Pagination(total=total, items=items, finished=finished)
