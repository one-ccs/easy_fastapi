#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core import (
    FailureException,
    Result,
    verify_password,
    create_access_token,
)
from app import schemas, models


async def login(form_data: OAuth2PasswordRequestForm, db: Session):
    user = models.crud.get_user_by_username(db, username=form_data.username)
    if not user:
        raise FailureException('未找到该用户')
    if not verify_password(form_data.password, user.hashed_password):
        raise FailureException('密码错误')
    # return Result.success('登录成功', data={
    #     'email': user.email,
    #     'username': user.username,
    #     'avatar_url': user.avatar_url,
    #     'access_token': create_access_token({
    #         'username': user.username,
    #         'is_active': user.is_active,
    #     }),
    #     'token_type': 'bearer',
    # })
    return {
        'email': user.email,
        'username': user.username,
        'avatar_url': user.avatar_url,
        'access_token': create_access_token({
            'username': user.username,
            'is_active': user.is_active,
        }),
        'token_type': 'bearer',
    }


async def register(user: schemas.UserCreate, db: Session):
    if not user.username and not user.email:
        raise FailureException('用户名和邮箱不能同时为空')
    if user.username and models.crud.get_user_by_username(db, username=user.username):
        raise FailureException('用户名已存在')
    if user.email and models.crud.get_user_by_email(db, email=user.email):
        raise FailureException('邮箱已存在')
    return Result.success('注册成功', data=models.crud.create_user(db, user))


async def logout(user):
    return Result.success(data=user)
