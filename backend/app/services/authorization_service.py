#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.core import (
    FailureException,
    Result,
    TokenData,
    verify_password,
    decode_token,
    revoke_token,
    create_access_token,
    create_refresh_token,
)
from app import schemas, models


async def login(form_data: OAuth2PasswordRequestForm, db: Session):
    user = models.crud.get_user_by_username_or_email(db, form_data.username)
    if not user:
        raise FailureException('用户名或邮箱不存在')
    if not verify_password(form_data.password, user.hashed_password):
        raise FailureException('密码错误')

    access_token = create_access_token(sub=user.username)
    refresh_token = create_refresh_token(sub=user.username)

    return Result('登录成功', data={
        'user_info': user,
        'token_type': 'bearer',
        'access_token': access_token,
        'refresh_token': refresh_token,
    })


async def refresh(current_user: TokenData):
    access_token = create_access_token(sub=current_user.sub)

    return Result('刷新令牌成功', data={
        'token_type': 'bearer',
        'access_token': access_token,
    })


async def register(form_data: schemas.UserCreate, db: Session):
    if not form_data.username and not form_data.email:
        raise FailureException('用户名和邮箱不能同时为空')
    if form_data.username and models.crud.get_user_by_username(db, username=form_data.username):
        raise FailureException('用户名已存在')
    if form_data.email and models.crud.get_user_by_email(db, email=form_data.email):
        raise FailureException('邮箱已存在')
    user = models.crud.create_user(db, form_data)

    return Result('注册成功', data={
        'username': user.username or user.email,
    })


async def logout(refresh_token: str, access_token: str):
    refresh_payload = decode_token(refresh_token)
    access_payload = decode_token(access_token)

    if not refresh_payload.isr or refresh_payload.sub != access_payload.sub:
        raise FailureException('非法的刷新令牌')

    revoke_token(refresh_token)
    revoke_token(access_token)

    return Result('登出成功')
