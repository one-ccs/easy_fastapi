#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services import user_service
from app import schemas, models

user_router = APIRouter(
    prefix='/users',
    tags=['用户'],
)


@user_router.get('/{user_id}', summary='查询用户信息')
async def user_get(user_id: int, db: Session = Depends(models.get_db)):
    return await user_service.get(user_id, db)


@user_router.put('/', summary='添加用户')
async def user_add(user: schemas.UserCreate, db: Session = Depends(models.get_db)):
    return await user_service.add(user, db)


@user_router.post('/', summary='修改用户')
async def user_modify():
    return await user_service.modify()


@user_router.delete('/', summary='删除用户')
async def user_delete():
    return await user_service.delete()


@user_router.get('/users', summary='获取用户列表')
async def user_get_users():
    return await user_service.get_users()


@user_router.post('/login', summary='登录', description='用户登录接口')
async def user_login():
    return await user_service.login()


@user_router.post('/logout', summary='登出', description='用户登出接口')
async def user_logout():
    return await user_service.logout()
