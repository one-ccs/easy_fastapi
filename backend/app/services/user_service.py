#!/usr/bin/env python
# -*- coding: utf-8 -*-
from app.core import (
    TODOException,
    FailureException,
    Result,
    encrypt_password,
)
from app import schemas, models


async def get(id: int):
    db_user = models.User.by_id(id)
    return Result(data=db_user)


async def add(user: schemas.UserCreate):
    if not user.username and not user.email:
        raise FailureException('用户名和邮箱不能同时为空')

    if user.username and models.User.by_username(user.username):
        raise FailureException('用户名已存在')

    if user.email and models.User.by_email(user.email):
        raise FailureException('邮箱已存在')

    db_user = models.User.create(user)
    db_user.hashed_password = encrypt_password(user.password)
    db_user.save_or_update()
    # TODO 设置默认角色

    return Result(data=db_user)


async def modify(user: schemas.UserModify):
    db_user = models.User.by_id(user.id)
    db_user.sqlmodel_update(user.model_dump(exclude={'id'}, exclude_unset=True))

    if user.password:
        db_user.hashed_password = encrypt_password(user.password)

    db_user.save_or_update()

    return Result(data=db_user)


async def delete(ids: list[int]):
    count = models.User.query(models.User.id.in_(ids)).delete_all()

    return Result(data=count)


async def page():
    raise TODOException()


async def get_user_roles(id: int):
    db_roles = models.User.get_roles(id)
    return Result(data=db_roles)
