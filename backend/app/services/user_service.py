#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session

from app.exceptions import TODOException, FailureException
from app.utils import Result
from app import models, schemas


async def get(user_id: int, db: Session):
    db_user = models.crud.get_user(db, user_id)
    return Result.success(data=db_user, schemas=schemas.User)


async def add(user: schemas.UserCreate, db: Session):
    db_user = models.crud.get_user_by_email(db, user.email)
    if db_user:
        raise FailureException('已存在该邮箱地址')
    db_user = models.crud.create_user(db, user)
    return Result.success(data=db_user, schemas=schemas.User)


async def modify():
    raise TODOException()


async def delete():
    raise TODOException()


async def get_users():
    return Result.success()

async def login():
    return Result.success('登录成功')


async def logout():
    raise TODOException()


async def register():
    raise TODOException()
