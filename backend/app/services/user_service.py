#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlmodel import or_

from app.core import (
    TODOException,
    FailureException,
    Result,
    encrypt_password,
)
from app import models, schemas


async def get(user_id: int):
    db_user = models.User.by_id(user_id)
    return Result(data=db_user)


async def add(user: schemas.UserCreate):
    db_user = models.User.by_username(user.username)
    if db_user:
        raise FailureException('用户名已存在')

    db_user = models.User.by_email(user.email)
    if db_user:
        raise FailureException('邮箱已存在')

    db_user = models.User.create(user)
    db_user.hashed_password = encrypt_password(user.password)
    db_user.save_or_update()
    # TODO 设置默认角色
    return Result(data=db_user)


async def modify():
    raise TODOException()


async def delete():
    raise TODOException()


async def page():
    raise TODOException()


async def get_user_roles(user_id: int):
    db_roles = models.User.get_roles(user_id)
    return Result(data=db_roles)
