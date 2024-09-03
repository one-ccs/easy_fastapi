#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services import user_service
from app import core, schemas, models


user_router = APIRouter()


@user_router.get('', summary='查询用户信息', response_model=schemas.ResultUser)
async def get(
    user_id: int,
    current_user: schemas.UserInToken = Depends(core.get_current_user),
    db: Session = Depends(core.get_db),
):
    return await user_service.get(user_id, db)


@user_router.put('', summary='添加用户', response_model=schemas.ResultUser)
async def add(
    user: schemas.UserCreate,
    current_user: schemas.UserInToken = Depends(core.get_current_user),
    db: Session = Depends(core.get_db)
):
    return await user_service.add(user, db)


@user_router.post('', summary='修改用户')
async def modify(
    current_user: schemas.UserInToken = Depends(core.get_current_user),
):
    return await user_service.modify()


@user_router.delete('', summary='删除用户')
async def delete(
    current_user: schemas.UserInToken = Depends(core.get_current_user),
):
    return await user_service.delete()


@user_router.get('/page', summary='获取用户列表')
async def get_page(
    current_user: schemas.UserInToken = Depends(core.get_current_user),
):
    return await user_service.get_page()
