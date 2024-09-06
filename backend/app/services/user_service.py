#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlmodel import Session

from app.core import TODOException, FailureException, Result
from app import models, schemas


async def get(user_id: int, db: Session):
    db_user = models.crud.get_user(db, user_id)
    return Result(data=db_user)


async def add(user: schemas.UserCreate, db: Session):
    db_user = models.crud.get_user_by_email(db, user.email)
    if db_user:
        raise FailureException('已存在该邮箱地址')
    db_user = models.crud.create_user(db, user)
    return Result(data=db_user)


async def modify():
    raise TODOException()


async def delete():
    raise TODOException()


async def page():
    raise TODOException()


async def get_user_roles(user_id: int, db: Session):
    db_roles = models.crud.get_user_roles(db, user_id)
    return Result(data=db_roles)
