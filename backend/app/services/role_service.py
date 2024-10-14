#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tortoise.expressions import Q

from app.core import (
    FailureException,
    Result,
)
from app import schemas, models


async def get(id: int):
    db_role = await models.Role.by_id(id)

    if not db_role:
        raise FailureException('Role 不存在')

    return Result(data=db_role)


async def add(role: schemas.RoleCreate):
    db_role = models.Role(
        **role.model_dump(exclude_unset=True),
    )
    await db_role.save()

    return Result(data=db_role)


async def modify(role: schemas.RoleModify):
    db_role = await models.Role.by_id(role.id)

    if not db_role:
        raise FailureException('Role 不存在')


    db_role.update_from_dict(
        role.model_dump(exclude={'id'}, exclude_unset=True),
    )
    await db_role.save()

    return Result(data=db_role)


async def delete(ids: list[int]):
    count = await models.Role.filter(id__in=ids).delete()

    return Result(data=count)


async def page(page_query: schemas.PageQuery):
    pagination = await models.Role.paginate(
        page_query.page,
        page_query.size,
        Q(role__icontains=page_query.query),
    )

    return Result(data=pagination)
