#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi.security import OAuth2PasswordRequestForm

from app.core import (
    FailureException,
    Result,
    TokenData,
    verify_password,
    encrypt_password,
    decode_token,
    revoke_token,
    create_access_token,
    create_refresh_token,
)
from app import schemas, models


async def token(form_data: OAuth2PasswordRequestForm):
    db_user = await models.User.by_username_or_email(form_data.username)

    if not db_user:
        raise FailureException('用户名或邮箱不存在')

    if not verify_password(form_data.password, db_user.hashed_password):
        raise FailureException('密码错误')

    access_token = create_access_token(sub=form_data.username)
    refresh_token = create_refresh_token(sub=form_data.username)

    return {
        'token_type': 'bearer',
        'access_token': access_token,
        'refresh_token': refresh_token,
    }


async def login(form_data: OAuth2PasswordRequestForm):
    db_user = await models.User.by_username_or_email(form_data.username)

    if not db_user:
        raise FailureException('用户名或邮箱不存在')

    if not verify_password(form_data.password, db_user.hashed_password):
        raise FailureException('密码错误')

    access_token = create_access_token(sub=form_data.username)
    refresh_token = create_refresh_token(sub=form_data.username)

    return Result('登录成功', data={
        'user': {
            **db_user(),
            'roles': await db_user.get_roles(),
        },
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


async def register(form_data: schemas.Register):
    if not form_data.username and not form_data.email:
        raise FailureException('用户名和邮箱不能同时为空')

    if form_data.username and await models.User.by_username(form_data.username):
        raise FailureException('用户名已存在')

    if form_data.email and await models.User.by_email(form_data.email):
        raise FailureException('邮箱已存在')

    db_user = models.User(
        **vars(form_data),
        hashed_password=encrypt_password(form_data.password),
    )
    await db_user.save()
    # TODO 没有角色时，创建默认角色
    await db_user.roles.add(await models.Role.get_or_create(role='user'))

    return Result('注册成功', data={
        'username': db_user.username or db_user.email,
    })


async def logout(refresh_token: str, access_token: str):
    refresh_payload = decode_token(refresh_token)
    access_payload = decode_token(access_token)

    if not refresh_payload.isr or refresh_payload.sub != access_payload.sub:
        raise FailureException('非法的刷新令牌')

    revoke_token(refresh_token)
    revoke_token(access_token)

    return Result('登出成功')
