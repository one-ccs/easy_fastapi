#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Any

from fastapi import FastAPI, Request
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidSignatureError,
    DecodeError,
    InvalidTokenError,
    PyJWTError,
)

from ..exception import (
    UnauthorizedException,
    ForbiddenException,
    FailureException,
)
from ..logger import uvicorn_logger
from ..result import JSONResponseResult
from ..persistence import Persistence
from ..config import Config
from .global_var import (
    AUTH_TYPE,
)
from .models import UserMixin
from .schemas import (
    Token,
    APIToken,
    APIRefresh,
    APILogin,
)
from .utils import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


persistence = Persistence()
config = Config()


class AuthenticationHandler:
    """认证处理器基类"""

    async def load_user(self, username: str) -> UserMixin:
        """用于从数据库加载用户

        Args:
            username (str): 用户名

        Returns:
            UserMixin: 用户模型

        Raises:
            FailureException: 用户不存在
        """
        raise NotImplementedError()

    async def verify_user(self, form_data: OAuth2PasswordRequestForm, db_user: UserMixin) -> None:
        """用于登录时验证用户

        Args:
            form_data (OAuth2PasswordRequestForm): 表单数据
            db_user (UserMixin): 用户信息

        Raises:
            FailureException: 密码错误
            ForbiddenException: 用户无权访问
        """
        raise NotImplementedError()

    async def verify_token(self, token: str) -> None:
        """用于验证令牌

        Args:
            token (str): 令牌

        Raises:
            UnauthorizedException: 令牌已销毁
            ForbiddenException: 令牌无效
        """
        raise NotImplementedError()

    async def authenticate(self, token: Token, scopes: list[str]) -> None:
        """用于验证令牌权限

        Args:
            token (Token): 令牌
            scopes (list[str]): 权限列表

        Raises:
            ForbiddenException: 无访问权限
        """
        raise NotImplementedError()

    async def token(self, form_data: OAuth2PasswordRequestForm) -> APIToken:
        """获取令牌 API

        Args:
            form_data (OAuth2PasswordRequestForm): 表单数据

        Returns:
            APIToken: 响应信息
        """
        raise NotImplementedError()

    async def refresh(self, token: Token):
        """刷新令牌 API

        Args:
            token (Token): 刷新令牌

        Returns:
            APIRefresh: 响应信息

        Raises:
            ForbiddenException: 需要刷新令牌
            FailureException: 刷新失败
        """
        raise NotImplementedError()

    async def login(self, form_data: OAuth2PasswordRequestForm) -> APILogin:
        """登录 API

        Args:
            form_data (OAuth2PasswordRequestForm): 表单数据

        Returns:
            APILogin: 响应信息

        Raises:
            UnauthorizedException: 用户名或密码错误
        """
        raise NotImplementedError()

    async def logout(self, refresh_token: str, access_token: str) -> Any:
        """登出 API

        Args:
            refresh_token (str): 刷新令牌
            access_token (str): 访问令牌

        Raises:
            FailureException: 登出失败
        """
        raise NotImplementedError()


class AuthHandler(AuthenticationHandler):
    """实现认证处理器"""

    async def verify_user(self, form_data: OAuth2PasswordRequestForm, db_user: UserMixin) -> None:
        if not await verify_password(form_data.password, db_user.h_pwd):
            raise FailureException('密码错误')

    async def verify_token(self, token: str) -> None:
        if persistence.get(token):
            raise UnauthorizedException('令牌已销毁')

    async def authenticate(self, token: Token, scopes: list[str]) -> None:
        if not token.has_permission(scopes):
            raise ForbiddenException('无访问权限')

    async def __login(self, form_data: OAuth2PasswordRequestForm) -> tuple[UserMixin, str, str]:
        db_user = await self.load_user(form_data.username)

        await self.verify_user(form_data, db_user)

        access_token = await create_access_token(sub=db_user.identity, sco=db_user.scopes)
        refresh_token = await create_refresh_token(sub=db_user.identity, sco=db_user.scopes)

        return {'username': db_user.identity, 'scopes': db_user.scopes}, access_token, refresh_token

    async def token(self, form_data: OAuth2PasswordRequestForm) -> APIToken:
        _, access_token, refresh_token = await self.__login(form_data)

        return APIToken(
            token_type=AUTH_TYPE,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh(self, refresh_token: Token):
        access_token = await create_access_token(sub=refresh_token.sub, sco=refresh_token.sco)

        return APIRefresh(
            token_type=AUTH_TYPE,
            access_token=access_token,
        )

    async def login(self, form_data: OAuth2PasswordRequestForm) -> APILogin:
        db_user, access_token, refresh_token = await self.__login(form_data)

        return APILogin(
            user=db_user,
            token_type=AUTH_TYPE,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def logout(self, refresh_token: str, access_token: str) -> Any:
        _refresh_token: Token = await decode_token(refresh_token)
        _access_token: Token = await decode_token(access_token)

        if not _refresh_token.isr:
            raise FailureException('参数错误，需要刷新令牌')

        if _refresh_token.sub != _access_token.sub:
            raise ForbiddenException()

        persistence.set(access_token, 1, config.easy_fastapi.authentication.access_token_expire_minutes)
        persistence.set(refresh_token, 1, config.easy_fastapi.authentication.refresh_token_expire_minutes)


def binding_exception_handler(app: FastAPI):
    @app.exception_handler(ExpiredSignatureError)
    async def jwt_exception_handler_1(request: Request, exc: ExpiredSignatureError):
        return JSONResponseResult.unauthorized('令牌已过期')

    @app.exception_handler(InvalidSignatureError)
    async def jwt_exception_handler_2(request: Request, exc: InvalidSignatureError):
        return JSONResponseResult.unauthorized('无效的签名')

    @app.exception_handler(DecodeError)
    async def jwt_exception_handler_3(request: Request, exc: DecodeError):
        return JSONResponseResult.unauthorized('令牌解析失败')

    @app.exception_handler(InvalidTokenError)
    async def jwt_exception_handler_4(request: Request, exc: InvalidTokenError):
        return JSONResponseResult.unauthorized('无效的访问令牌')

    @app.exception_handler(PyJWTError)
    async def jwt_exception_handler_5(request: Request, exc: PyJWTError):
        uvicorn_logger.error(msg=f"未知令牌错误", exc_info=exc)
        return JSONResponseResult.unauthorized('未知令牌错误')
