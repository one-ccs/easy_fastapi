#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from typing import Type, TypeVar, Generic, Any, Optional
from dataclasses import dataclass

from tortoise import Tortoise, Model
from tortoise.expressions import Q
from tortoise.query_utils import Prefetch
from easy_pyoc import Logger

from .config import Config

_TModel = TypeVar('_TModel', bound=Model)


async def init_tortoise(config: Optional[dict] = None):
    _config = Config()

    if _config.database.echo:
        Logger(name='tortoise', fmt='%(levelname)-8s : %(message)s')

    await Tortoise.init(config=config or {
        'connections': {
            'default': _config.database.uri,
        },
        'apps': {
            'models': {
                'models': ['aerich.models', 'app.models'],
                'default_connection': 'default',
            },
        },
        'use_tz': False,
        'timezone': _config.database.timezone,
    })


async def generate_schemas(config: dict):
    await Tortoise.init(config=config)
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
