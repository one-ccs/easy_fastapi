#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from easy_fastapi import Result
from easy_fastapi.authentication import BaseUser
from app.services import user_service
from app import schemas, auth


user_router = APIRouter()


@user_router.post('/register', summary='注册', response_model=Result[BaseUser])
async def register(form_data: Annotated[schemas.Register, Depends()]):
    return await user_service.register(form_data)


@user_router.get('', summary='查询用户信息', response_model=Result[schemas.User])
@auth.require
async def get(id: int):
    return await user_service.get(id)


@user_router.post('', summary='添加用户', response_model=Result[schemas.User])
@auth.require
async def add(user: schemas.UserCreate):
    return await user_service.add(user)


@user_router.put('', summary='修改用户', response_model=Result[schemas.User])
@auth.require
async def modify(user: schemas.UserModify):
    return await user_service.modify(user)


@user_router.delete('', summary='删除用户', response_model=Result[int])
@auth.require
async def delete(ids: list[int] = Query(...)):
    return await user_service.delete(ids)


@user_router.get('/page', summary='获取用户列表', response_model=Result[schemas.PageQueryOut[schemas.User]])
@auth.require
async def page(page_query: schemas.PageQuery):
    return await user_service.page(page_query)


@user_router.get('/roles', summary='获取用户角色', response_model=Result[list[schemas.Role]])
@auth.require
async def get_user_roles(id: int):
    return await user_service.get_user_roles(id)
