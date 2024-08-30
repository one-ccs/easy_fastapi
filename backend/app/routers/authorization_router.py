#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core import get_current_active_user
from app.services import authorization_service
from app import schemas, models


authorization_router = APIRouter()


@authorization_router.post('/login', summary='登录', description='用户登录接口')
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(models.get_db)):
    return await authorization_service.login(form_data, db)


@authorization_router.post('/register', summary='注册', description='用户注册接口')
async def register(user: schemas.UserCreate, db: Session = Depends(models.get_db)):
    return await authorization_service.register(user, db)


@authorization_router.post('/logout', summary='登出', description='用户登出接口')
async def logout(current_user: dict = Depends(get_current_active_user)):
    return await authorization_service.logout(current_user)
