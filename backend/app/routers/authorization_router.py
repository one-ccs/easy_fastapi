#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from app.services import authorization_service
from app import core, schemas


authorization_router = APIRouter()


@authorization_router.post('/login', summary='登录', description='用户登录接口')
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(core.get_db),
):
    return await authorization_service.login(form_data, db)


@authorization_router.post('/refresh', summary='刷新令牌', description='刷新令牌接口')
async def refresh(
    current_user: schemas.UserInToken = Depends(core.get_current_of_refresh)
):
    return await authorization_service.refresh(current_user)


@authorization_router.post('/register', summary='注册', description='用户注册接口')
async def register(
    form_data: schemas.UserCreate,
    db: Session = Depends(core.get_db),
):
    return await authorization_service.register(form_data, db)


@authorization_router.post('/logout', summary='登出', description='用户登出接口')
async def logout(
    refresh_token: str,
    access_token: str = Depends(core.require_token),
):
    return await authorization_service.logout(refresh_token, access_token)
