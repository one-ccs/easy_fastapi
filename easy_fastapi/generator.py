#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Iterator
from pathlib import Path
from importlib import import_module
from pkgutil import iter_modules

from .logger import logger


class Generator:
    """代码生成器

    根据 models 生成对应的 router 和 service 代码"""

    def __init__(self, models_path: Iterator[str], pk_name: str = 'id', models_ignore: set[str] = {}, encoding: str = 'utf-8'):
        self.models_path = models_path
        self.pk_name = pk_name
        self.models_ignore = models_ignore
        self.encoding = encoding

        self.models = self.get_models()
        self.work_path = Path(models_path[0]).parent

    def get_models(self) -> list[str]:
        """获取 models"""
        return [model_name for _, model_name, _ in iter_modules(self.models_path) if model_name not in self.models_ignore]

    def get_fields_map(self, model_name: str) -> dict[str, str]:
        """获取 model 字段"""
        module = import_module(f'app.models.{model_name}')
        model = getattr(module, model_name.title())

        return {
            field: tortoise_type.field_type.__name__
            for field, tortoise_type in model._meta.fields_map.items()
            if tortoise_type.field_type
        }

    def generate_schemas(self):
        """生成 schemas 代码"""
        for model_name in self.models:
            file_name = f'{model_name}.py'
            init_path = self.work_path /'schemas' / '__init__.py'
            file_path = self.work_path /'schemas' / file_name
            fields_map = self.get_fields_map(model_name)
            base_fields = '\n    '.join(f'{k}: {v}' for k, v in fields_map.items() if k != self.pk_name)

            try:
                with open(file_path, 'w', encoding=self.encoding) as f:
                    f.write(SCHEMA_TEMPLATE.format(
                        model_name=model_name,
                        title_model_name=model_name.title(),
                        base_fields=base_fields,
                        pk_name=self.pk_name,
                        pk_type=fields_map.get(self.pk_name, 'int'),
                    ))
                with open(init_path, 'a', encoding=self.encoding) as f:
                    f.write(f'from .{model_name} import *\n')
            except Exception as e:
                logger.warning(f"生成 {file_name} 错误: {e}")

    def generate_routers(self):
        """生成 router 代码"""
        append_routes: list[str] = []

        for model_name in self.models:
            file_name = f'{model_name}_router.py'
            init_path = self.work_path / 'routers' / '__init__.py'
            file_path = self.work_path / 'routers' / file_name

            try:
                with open(file_path, 'w', encoding=self.encoding) as f:
                    f.write(ROUTER_TEMPLATE.format(model_name=model_name, title_model_name=model_name.title()))
                with open(init_path, 'a', encoding=self.encoding) as f:
                    f.write(f'from .{model_name}_router import {model_name}_router as {model_name}_router\n')
                append_routes.append(model_name)
            except Exception as e:
                logger.warning(f"生成 {file_name} 错误: {e}")

        try:
            main_init_path = self.work_path / '__init__.py'

            with open(main_init_path, 'a', encoding=self.encoding) as f:
                for model_name in append_routes:
                    f.write(f'from app.routers import {model_name}_router as {model_name}_router\n')

                f.write('\n')
                for model_name in append_routes:
                    f.write(f"app.include_router({model_name}_router, prefix='/{model_name}', tags=['{model_name.title()}'])\n")
        except Exception as e:
            logger.warning(f"追加路由到 {main_init_path} 错误: {e}")

    def generate_services(self):
        """生成 service 代码"""
        for model_name in self.models:
            file_name = f'{model_name}_service.py'
            init_path = self.work_path /'services' / '__init__.py'
            file_path = self.work_path /'services' / file_name

            try:
                with open(file_path, 'w', encoding=self.encoding) as f:
                    f.write(SERVICE_TEMPLATE.format(model_name=model_name, title_model_name=model_name.title()))
                with open(init_path, 'a', encoding=self.encoding) as f:
                    f.write(f'from . import {model_name}_service as {model_name}_service\n')
            except Exception as e:
                logger.warning(f"生成 {file_name} 错误: {e}")

    def build(self):
        """构建项目"""
        self.generate_schemas()
        self.generate_routers()
        self.generate_services()


SCHEMA_TEMPLATE = """#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime

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
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from easy_fastapi import (
    Result,
    JSONResult,
    Token,
    get_current_user,
)
from app.services import {model_name}_service
from app import schemas, auth


{model_name}_router = APIRouter()


@{model_name}_router.get('', summary='查询 {title_model_name} 信息', response_model=Result[schemas.{title_model_name}])
@auth.require
async def get(id: int):
    return await {model_name}_service.get(id)


@{model_name}_router.post('', summary='添加 {title_model_name}', response_model=Result[schemas.{title_model_name}])
@auth.require
async def add({model_name}: schemas.{title_model_name}Create):
    return await {model_name}_service.add({model_name})


@{model_name}_router.put('', summary='修改 {title_model_name}', response_model=Result[schemas.{title_model_name}])
@auth.require
async def modify({model_name}: schemas.{title_model_name}Modify):
    return await {model_name}_service.modify({model_name})


@{model_name}_router.delete('', summary='删除 {title_model_name}', response_model=Result[int])
@auth.require
async def delete(ids: list[int] = Query(...)):
    return await {model_name}_service.delete(ids)


@{model_name}_router.get('/page', summary='获取 {title_model_name} 列表', response_model=Result[schemas.PageQueryOut[schemas.{title_model_name}]])
@auth.require
async def page(page_query: Annotated[schemas.PageQuery, Depends()]):
    return await {model_name}_service.page(page_query)
"""

SERVICE_TEMPLATE = """#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tortoise.expressions import Q
from tortoise.exceptions import IntegrityError

from easy_fastapi import (
    FailureException,
    JSONResult,
)
from app import schemas, models


async def get(id: int):
    db_{model_name} = await models.{title_model_name}.by_id(id)

    if not db_{model_name}:
        raise FailureException('{title_model_name} 不存在')

    return JSONResult(data=db_{model_name})


async def add({model_name}: schemas.{title_model_name}Create):
    db_{model_name} = models.{title_model_name}(
        **{model_name}.model_dump(exclude_unset=True),
    )
    await db_{model_name}.save()

    return JSONResult(data=db_{model_name})


async def modify({model_name}: schemas.{title_model_name}Modify):
    db_{model_name} = await models.{title_model_name}.by_id({model_name}.id)

    if not db_{model_name}:
        raise FailureException('{title_model_name} 不存在')


    db_{model_name}.update_from_dict(
        {model_name}.model_dump(exclude={{'id'}}, exclude_unset=True),
    )
    try:
        await db_{model_name}.save()
    except IntegrityError:
        raise FailureException('{title_model_name} 已存在')

    return JSONResult(data=db_{model_name})


async def delete(ids: list[int]):
    count = await models.{title_model_name}.filter(id__in=ids).delete()

    return JSONResult(data=count)


async def page(page_query: schemas.PageQuery):
    pagination = await models.{title_model_name}.paginate(
        page_query.page,
        page_query.size,
    )

    return JSONResult(data=pagination)
"""
