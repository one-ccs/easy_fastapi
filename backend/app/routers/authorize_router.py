#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.security import OAuth2PasswordRequestForm

from app.core import (
    Result,
    TokenData,
    require_token,
    get_current_refresh_user,
)
from app.services import authorize_service
from app import schemas


authorization_router = APIRouter()


@authorization_router.post(
    '/login',
    summary='登录',
    description='用户登录接口',
    response_model=Result.of(schemas.UserLogin))
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    return await authorize_service.login(form_data)


@authorization_router.post(
    '/refresh',
    summary='刷新令牌',
    description='刷新令牌接口',
    response_model=Result.of(schemas.RefreshToken))
async def refresh(
    current_user: TokenData = Depends(get_current_refresh_user),
):
    return await authorize_service.refresh(current_user)


@authorization_router.post(
    '/register',
    summary='注册',
    description='用户注册接口',
    response_model=Result.of(schemas.Register))
async def register(
    form_data: schemas.UserCreate,
):
    return await authorize_service.register(form_data)


@authorization_router.post(
    '/logout',
    summary='登出',
    description='用户登出接口',
    response_model=Result.of(None))
async def logout(
    x_token: Annotated[str, Header(..., alias='X-Token', description='刷新令牌')],
    access_token: str = Depends(require_token),
):
    return await authorize_service.logout(x_token, access_token)
