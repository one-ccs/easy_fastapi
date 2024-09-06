#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.core import (
    TokenData,
    get_db,
    require_token,
    get_current_refresh_user,
)
from app.services import authorization_service
from app import schemas


authorization_router = APIRouter()


@authorization_router.post('/login', summary='登录', description='用户登录接口')
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    return await authorization_service.login(form_data, db)


@authorization_router.post('/refresh', summary='刷新令牌', description='刷新令牌接口')
async def refresh(
    current_user: TokenData = Depends(get_current_refresh_user),
):
    return await authorization_service.refresh(current_user)


@authorization_router.post('/register', summary='注册', description='用户注册接口')
async def register(
    form_data: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    return await authorization_service.register(form_data, db)


@authorization_router.post('/logout', summary='登出', description='用户登出接口')
async def logout(
    refresh_token: str,
    access_token: str = Depends(require_token),
):
    return await authorization_service.logout(refresh_token, access_token)
