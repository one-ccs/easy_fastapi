#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tortoise.expressions import Q
from tortoise.exceptions import IntegrityError

from easy_fastapi import (
    FailureException,
    JSONResult,
)
from easy_fastapi.authentication import encrypt_password
from app import schemas, models


async def register(form_data: schemas.Register):
    if not form_data.username and not form_data.email:
        raise FailureException('用户名和邮箱不能同时为空')

    if form_data.username and await models.User.by_username(form_data.username):
        raise FailureException('用户名已存在')

    if form_data.email and await models.User.by_email(form_data.email):
        raise FailureException('邮箱已存在')

    db_user = models.User(
        **vars(form_data),
        hashed_password=await encrypt_password(form_data.password),
    )
    await db_user.save()

    default_role, _ = await models.Role.get_or_create(role='user', role_desc='用户')
    await db_user.roles.add(default_role)
    await db_user.fetch_related('roles')

    return JSONResult('注册成功', data=db_user)


async def get(id: int):
    db_user = await models.User.by_id(id, ('roles', ))

    if not db_user:
        raise FailureException('用户不存在')

    return JSONResult(data=db_user)


async def add(user: schemas.UserCreate):
    if not user.username and not user.email:
        raise FailureException('用户名和邮箱不能同时为空')

    if user.username and await models.User.by_username(user.username):
        raise FailureException('用户名已存在')

    if user.email and await models.User.by_email(user.email):
        raise FailureException('邮箱已存在')

    db_user = models.User(
        **user.model_dump(exclude={'password'}, exclude_unset=True),
        hashed_password=await encrypt_password(user.password),
    )
    await db_user.save()

    default_role, _ = await models.Role.get_or_create(role='user', role_desc='用户')
    await db_user.roles.add(default_role)

    return JSONResult(data=db_user)


async def modify(user: schemas.UserModify):
    db_user = await models.User.by_id(user.id, ('roles', ))

    if not db_user:
        raise FailureException('用户不存在')

    if user.password:
        db_user.hashed_password = await encrypt_password(user.password)

    db_user.update_from_dict(
        user.model_dump(exclude={'id'}, exclude_unset=True),
    )
    try:
        await db_user.save()
    except IntegrityError:
        raise FailureException('用户名或邮箱已存在')

    return JSONResult(data=db_user)


async def delete(ids: list[int]):
    count = await models.User.filter(id__in=ids).delete()

    return JSONResult(data=count)


async def page(page_query: schemas.PageQuery):
    pagination = await models.User.paginate(
        page_query.page,
        page_query.size,
        ('roles', ),
        Q(username__icontains=page_query.query) | Q(email__icontains=page_query.query),
    )
    return JSONResult(data=pagination)


async def get_user_roles(id: int):
    db_user = await models.User.by_id(id, ('roles', ))

    if not db_user:
        raise FailureException('用户不存在')

    return JSONResult(data=db_user.roles)
