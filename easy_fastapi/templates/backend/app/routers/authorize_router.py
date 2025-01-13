#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.security import OAuth2PasswordRequestForm

from easy_fastapi import (
    FailureException,
    Result,
    TokenData,
    decode_token,
    require_token,
    get_current_refresh_user,
)
from app.services import authorize_service
from app import schemas


authorize_router = APIRouter()


@authorize_router.post(
    '/token',
    summary='获取令牌',
    description='获取令牌接口',
    response_model=schemas.TokenOut)
async def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    return await authorize_service.token(form_data)


@authorize_router.post(
    '/login',
    summary='登录',
    description='用户登录接口',
    response_model=Result.of(schemas.LoginOut))
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    return await authorize_service.login(form_data)


@authorize_router.post(
    '/register',
    summary='注册',
    description='用户注册接口',
    response_model=Result.of(schemas.RegisterOut))
async def register(
    form_data: schemas.Register = Depends(),
):
    return await authorize_service.register(form_data)


@authorize_router.post(
    '/logout',
    summary='登出',
    description='用户登出接口',
    response_model=Result.of(None))
async def logout(
    x_token: Annotated[str, Header(..., alias='X-Token', description='刷新令牌')],
    access_token: str = Depends(require_token),
):
    refresh_payload = decode_token(x_token)
    access_payload = decode_token(access_token)

    if not refresh_payload.isr or refresh_payload.sub != access_payload.sub:
        raise FailureException('非法的刷新令牌')

    return await authorize_service.logout(x_token, access_token)


@authorize_router.post(
    '/refresh',
    summary='刷新令牌',
    description='刷新令牌接口',
    response_model=Result.of(schemas.RefreshTokenOut))
async def refresh(
    current_user: TokenData = Depends(get_current_refresh_user),
):
    return await authorize_service.refresh(current_user)
