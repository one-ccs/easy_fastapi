#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tortoise.expressions import Q

from app.core import (
    FailureException,
    Result,
    encrypt_password,
)
from app import schemas, models


async def get(id: int):
    db_user = await models.User.by_id(id)

    if not db_user:
        raise FailureException('用户不存在')

    return Result(data={
        **db_user(),
        'roles': await db_user.get_roles(),
    })


async def add(user: schemas.UserCreate):
    if not user.username and not user.email:
        raise FailureException('用户名和邮箱不能同时为空')

    if user.username and await models.User.by_username(user.username):
        raise FailureException('用户名已存在')

    if user.email and await models.User.by_email(user.email):
        raise FailureException('邮箱已存在')

    db_user = models.User(
        **user.model_dump(exclude={'password'}),
        hashed_password=encrypt_password(user.password),
    )
    await db_user.save()
    await db_user.roles.add(await models.Role.get(role='user'))

    return Result(data={
        **db_user(),
        'roles': await db_user.get_roles(),
    })


async def modify(user: schemas.UserModify):
    db_user = await models.User.by_id(user.id)

    if not db_user:
        raise FailureException('用户不存在')

    if user.password:
        db_user.hashed_password = encrypt_password(user.password)

    db_user.update_from_dict(
        user.model_dump(exclude={'id'}, exclude_unset=True),
    )
    await db_user.save()

    return Result(data={
        **db_user(),
        'roles': await db_user.get_roles(),
    })


async def delete(ids: list[int]):
    count = await models.User.filter(id__in=ids).delete()

    return Result(data=count)


async def page(page_query: schemas.PageQuery):
    pagination = await models.User.paginate(
        page_query.page,
        page_query.size,
        Q(username__icontains=page_query.query) | Q(email__icontains=page_query.query),
    )

    return Result(data={
        'total': pagination.total,
        'items': [{
            **item(),
            'roles': await item.get_roles(),
        } for item in pagination.items],
        'finished': pagination.finished,
    })


async def get_user_roles(id: int):
    db_user = await models.User.by_id(id)

    if not db_user:
        raise FailureException('用户不存在')

    db_roles = await db_user.get_roles()

    return Result(data=db_roles)
