#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, Query

from easy_fastapi import (
    Result,
    Token,
)
from app.services import role_service
from app import schemas, easy_fastapi


role_router = APIRouter()


@role_router.get('', summary='查询 Role 信息', response_model=Result.of(schemas.Role))
@easy_fastapi.auth.require
async def get(id: int):
    return await role_service.get(id)


@role_router.post('', summary='添加 Role', response_model=Result.of(schemas.Role))
@easy_fastapi.auth.require
async def add(role: schemas.RoleCreate):
    return await role_service.add(role)


@role_router.put('', summary='修改 Role', response_model=Result.of(schemas.Role))
@easy_fastapi.auth.require
async def modify(role: schemas.RoleModify):
    return await role_service.modify(role)


@role_router.delete('', summary='删除 Role', response_model=Result.of(int, name='Delete'))
@easy_fastapi.auth.require
async def delete(ids: list[int] = Query(...)):
    return await role_service.delete(ids)


@role_router.get('/page', summary='获取 Role 列表', response_model=Result.of(schemas.PageQueryOut[schemas.Role]))
@easy_fastapi.auth.require
async def page(page_query: schemas.PageQuery = Depends()):
    return await role_service.page(page_query)
