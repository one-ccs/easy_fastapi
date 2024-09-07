#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core import (
    Result,
    TokenData,
    get_db,
    get_current_user,
)
from app.services import user_service
from app import schemas


user_router = APIRouter()


@user_router.get('', summary='查询用户信息', response_model=Result.of(schemas.UserInfo))
async def get(
    user_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await user_service.get(user_id, db)


@user_router.put('', summary='添加用户', response_model=Result.of(schemas.UserInfo))
async def add(
    user: schemas.UserCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return await user_service.add(user, db)


@user_router.post('', summary='修改用户')
async def modify(
    current_user: TokenData = Depends(get_current_user),
):
    return await user_service.modify()


@user_router.delete('', summary='删除用户')
async def delete(
    current_user: TokenData = Depends(get_current_user),
):
    return await user_service.delete()


@user_router.get('/page', summary='获取用户列表')
async def page(
    current_user: TokenData = Depends(get_current_user),
):
    return await user_service.page()


@user_router.get('/roles', summary='获取用户角色', response_model=Result.of(list[schemas.Role], class_name='Roles'))
async def get_user_roles(
    user_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await user_service.get_user_roles(user_id, db)
