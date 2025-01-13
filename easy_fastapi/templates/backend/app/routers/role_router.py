#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, Query

from easy_fastapi import (
    Result,
    TokenData,
    get_current_user,
)
from app.services import role_service
from app import schemas


role_router = APIRouter()


@role_router.get('', summary='查询 Role 信息', response_model=Result.of(schemas.Role))
async def get(
    id: int,
    current_user: TokenData = Depends(get_current_user),
):
    return await role_service.get(id)


@role_router.post('', summary='添加 Role', response_model=Result.of(schemas.Role))
async def add(
    role: schemas.RoleCreate,
    current_user: TokenData = Depends(get_current_user),
):
    return await role_service.add(role)


@role_router.put('', summary='修改 Role', response_model=Result.of(schemas.Role))
async def modify(
    role: schemas.RoleModify,
    current_user: TokenData = Depends(get_current_user),
):
    return await role_service.modify(role)


@role_router.delete('', summary='删除 Role', response_model=Result.of(int, name='Delete'))
async def delete(
    ids: list[int] = Query(...),
    current_user: TokenData = Depends(get_current_user),
):
    return await role_service.delete(ids)


@role_router.get('/page', summary='获取 Role 列表', response_model=Result.of(schemas.PageQueryOut[schemas.Role]))
async def page(
    page_query: schemas.PageQuery = Depends(),
    current_user: TokenData = Depends(get_current_user),
):
    return await role_service.page(page_query)
