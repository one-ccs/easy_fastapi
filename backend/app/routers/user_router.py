#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services import user_service
from app import schemas, models


user_router = APIRouter()


@user_router.get('/{user_id}', summary='查询用户信息')
async def get(user_id: int, db: Session = Depends(models.get_db)):
    return await user_service.get(user_id, db)


@user_router.put('/', summary='添加用户')
async def add(user: schemas.UserCreate, db: Session = Depends(models.get_db)):
    return await user_service.add(user, db)


@user_router.post('/', summary='修改用户')
async def modify():
    return await user_service.modify()


@user_router.delete('/', summary='删除用户')
async def delete():
    return await user_service.delete()


@user_router.get('/users', summary='获取用户列表')
async def get_page(current_user: schemas.User = Depends()):
    return await user_service.get_page()
