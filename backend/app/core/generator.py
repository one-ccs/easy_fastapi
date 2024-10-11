#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Iterator
from pathlib import Path
import pkgutil


class Generator:
    """代码生成器

    根据 models 生成对应的 router 和 service 代码"""

    def __init__(self, models_path: Iterator[str]):
        self.models_path = models_path
        self.models = self.__get_models()
        self.work_path = Path(models_path[0]).parent

    def __get_models(self) -> list[str]:
        return [model_name for _, model_name, _ in pkgutil.iter_modules(self.models_path)]

    def generate_router(self):
        """生成 router 代码"""
        for model_name in self.models:
            file_name = f"_{model_name}_router.py"
            file_path = self.work_path / 'routers' / file_name

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(ROUTER_TEMPLATE.format(model_name=model_name, title_model_name=model_name.title()))

    def generate_service(self):
        """生成 service 代码"""
        for model_name in self.models:
            file_name = f"_{model_name}_service.py"
            file_path = self.work_path /'services' / file_name

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(SERVICE_TEMPLATE.format(model_name=model_name, title_model_name=model_name.title()))

    def build(self):
        """构建项目"""
        self.generate_router()
        self.generate_service()


ROUTER_TEMPLATE = """#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, Query

from app.core import (
    Result,
    TokenData,
    get_current_user,
)
from app.services import {model_name}_service
from app import schemas


{model_name}_router = APIRouter()


@{model_name}_router.get('', summary='{model_name}.GET', response_model=Result.of(schemas.{title_model_name}Out))
async def get(
    id: int,
    current_user: TokenData = Depends(get_current_user),
):
    return await {model_name}_service.get(id)


@{model_name}_router.post('', summary='{model_name}.POST', response_model=Result.of(schemas.{title_model_name}Out))
async def add(
    {model_name}: schemas.{title_model_name}Create,
    current_user: TokenData = Depends(get_current_user),
):
    return await {model_name}_service.add({model_name})


@{model_name}_router.put('', summary='{model_name}.PUT', response_model=Result.of(schemas.{title_model_name}Out))
async def modify(
    {model_name}: schemas.{title_model_name}Modify,
    current_user: TokenData = Depends(get_current_user),
):
    return await {model_name}_service.modify({model_name})


@{model_name}_router.delete('', summary='{model_name}.DELETE', response_model=Result.of(int, class_name='{title_model_name}Out'))
async def delete(
    ids: list[int] = Query(...),
    current_user: TokenData = Depends(get_current_user),
):
    return await {model_name}_service.delete(ids)


@{model_name}_router.get('/page', summary='{model_name}.GET.page', response_model=Result.of(schemas.PageQueryOut[schemas.{title_model_name}Out]))
async def page(
    page_query: schemas.PageQueryIn,
    current_user: TokenData = Depends(get_current_user),
):
    return await {model_name}_service.page(page_query)

"""

SERVICE_TEMPLATE = """#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tortoise.expressions import Q

from app.core import (
    FailureException,
    Result,
)
from app import schemas, models


async def get(id: int):
    db_{model_name} = await models.{title_model_name}.by_id(id)

    if not db_{model_name}:
        raise FailureException('{title_model_name} 不存在')

    return Result(data=db_{model_name})


async def add({model_name}: schemas.{title_model_name}Create):
    db_{model_name} = models.{title_model_name}(
        **{model_name}.model_dump(),
    )
    await db_{model_name}.save()

    return Result(data=db_{model_name})


async def modify({model_name}: schemas.{title_model_name}Modify):
    db_{model_name} = await models.{title_model_name}.by_id({model_name}.id)

    if not db_{model_name}:
        raise FailureException('{title_model_name} 不存在')


    db_{model_name}.update_from_dict(
        {model_name}.model_dump(exclude={{'id'}}, exclude_unset=True),
    )
    await db_{model_name}.save()

    return Result(data=db_{model_name})


async def delete(ids: list[int]):
    count = await models.{title_model_name}.filter(id__in=ids).delete()

    return Result(data=count)


async def page(page_query: schemas.PageQueryIn):
    db_{model_name}s = await models.{title_model_name}.filter(
        Q(username__icontains=page_query.query) | Q(email__icontains=page_query.query),
    ).limit(page_query.size).offset((page_query.page - 1) * page_query.size)

    return Result(data=db_{model_name}s)

"""
