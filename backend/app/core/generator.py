#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Iterator
from pathlib import Path
from importlib import import_module
import pkgutil


class Generator:
    """代码生成器

    根据 models 生成对应的 router 和 service 代码"""

    def __init__(self, models_path: Iterator[str], pk_name: str = 'id', models_ignore: set[str] = {}):
        self.models_path = models_path
        self.pk_name = pk_name
        self.models_ignore = models_ignore

        self.models = self.get_models()
        self.work_path = Path(models_path[0]).parent

    def get_models(self) -> list[str]:
        """获取 models"""
        return [model_name for _, model_name, _ in pkgutil.iter_modules(self.models_path) if model_name not in self.models_ignore]

    def get_fields_map(self, model_name: str) -> dict[str, str]:
        """获取 model 字段"""
        module = import_module(f'app.models.{model_name}')
        model = getattr(module, model_name.title())

        return {field: tortoise_type.field_type.__name__ for field, tortoise_type in model._meta.fields_map.items()}

    def generate_schemas(self):
        """生成 schemas 代码"""
        for model_name in self.models:
            file_name = f"{model_name}.py"
            file_path = self.work_path /'schemas' / file_name
            fields_map = self.get_fields_map(model_name)
            base_fields = '\n    '.join(f'{k}: {v}' for k, v in fields_map.items() if k != self.pk_name)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(SCHEMA_TEMPLATE.format(
                    model_name=model_name,
                    title_model_name=model_name.title(),
                    base_fields=base_fields,
                    pk_name=self.pk_name,
                    pk_type=fields_map.get(self.pk_name, 'int'),
                ))

    def generate_routers(self):
        """生成 router 代码"""
        for model_name in self.models:
            file_name = f"{model_name}_router.py"
            file_path = self.work_path / 'routers' / file_name

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(ROUTER_TEMPLATE.format(model_name=model_name, title_model_name=model_name.title()))

    def generate_services(self):
        """生成 service 代码"""
        for model_name in self.models:
            file_name = f"{model_name}_service.py"
            file_path = self.work_path /'services' / file_name

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(SERVICE_TEMPLATE.format(model_name=model_name, title_model_name=model_name.title()))

    def build(self):
        """构建项目"""
        self.generate_schemas()
        self.generate_routers()
        self.generate_services()


SCHEMA_TEMPLATE = """#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pydantic import BaseModel


class {title_model_name}Base(BaseModel):
    {base_fields}


class {title_model_name}({title_model_name}Base): ...


class {title_model_name}Create({title_model_name}Base): ...


class {title_model_name}Modify({title_model_name}Base):
    {pk_name}: {pk_type}
"""

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


@{model_name}_router.get('', summary='查询 {title_model_name} 信息', response_model=Result.of(schemas.{title_model_name}))
async def get(
    id: int,
    current_user: TokenData = Depends(get_current_user),
):
    return await {model_name}_service.get(id)


@{model_name}_router.post('', summary='添加 {title_model_name}', response_model=Result.of(schemas.{title_model_name}))
async def add(
    {model_name}: schemas.{title_model_name}Create,
    current_user: TokenData = Depends(get_current_user),
):
    return await {model_name}_service.add({model_name})


@{model_name}_router.put('', summary='修改 {title_model_name}', response_model=Result.of(schemas.{title_model_name}))
async def modify(
    {model_name}: schemas.{title_model_name}Modify,
    current_user: TokenData = Depends(get_current_user),
):
    return await {model_name}_service.modify({model_name})


@{model_name}_router.delete('', summary='删除 {title_model_name}', response_model=Result.of(int, name='Delete'))
async def delete(
    ids: list[int] = Query(...),
    current_user: TokenData = Depends(get_current_user),
):
    return await {model_name}_service.delete(ids)


@{model_name}_router.get('/page', summary='获取 {title_model_name} 列表', response_model=Result.of(schemas.PageQueryOut[schemas.{title_model_name}]))
async def page(
    page_query: schemas.PageQuery = Depends(),
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


async def page(page_query: schemas.PageQuery):
    pagination = await models.{title_model_name}.paginate(
        page_query.page,
        page_query.size,
    )

    return Result(data=pagination)
"""
