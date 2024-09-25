#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, Query

from app.core import (
    Result,
    TokenData,
    get_current_user,
)
from app.services import user_service
from app import schemas


user_router = APIRouter()


@user_router.get('', summary='查询用户信息', response_model=Result.of(schemas.UserInfo))
async def get(
    id: int,
    current_user: TokenData = Depends(get_current_user),
):
    return await user_service.get(id)


@user_router.post('', summary='添加用户', response_model=Result.of(schemas.UserInfo))
async def add(
    user: schemas.UserCreate,
    current_user: TokenData = Depends(get_current_user),
):
    return await user_service.add(user)


@user_router.put('', summary='修改用户', response_model=Result.of(schemas.UserInfo))
async def modify(
    user: schemas.UserModify,
    current_user: TokenData = Depends(get_current_user),
):
    return await user_service.modify(user)


@user_router.delete('', summary='删除用户', response_model=Result.of(int, class_name='UserDeleteOut'))
async def delete(
    ids: list[int] = Query(...),
    current_user: TokenData = Depends(get_current_user),
):
    return await user_service.delete(ids)


@user_router.get('/page', summary='获取用户列表', response_model=Result.of(schemas.PageQueryOut[schemas.UserInfo]))
async def page(
    page_query: schemas.PageQueryIn,
    current_user: TokenData = Depends(get_current_user),
):
    return await user_service.page(page_query)


@user_router.get('/roles', summary='获取用户角色', response_model=Result.of(list[schemas.Role], class_name='Roles'))
async def get_user_roles(
    id: int,
    current_user: TokenData = Depends(get_current_user),
):
    return await user_service.get_user_roles(id)
