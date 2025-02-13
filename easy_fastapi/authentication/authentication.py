#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Annotated, Optional, Callable
from typing_extensions import Doc
from functools import wraps
from inspect import Parameter, signature

from fastapi import (
    FastAPI,
    Depends,
    APIRouter,
)
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)

from ..exception import (
    UnauthorizedException,
    ForbiddenException,
)
from ..config import Config
from ..result import (
    Result,
    JSONResult,
)
from .models import UserMixin
from .schemas import (
    Token,
    APIToken,
    APILogin,
    APIRefresh,
)
from .utils import (
    Token,
    _async,
    decode_token,
)
from .handlers import (
    AuthenticationHandler,
    AuthHandler,
    binding_exception_handler,
)


class EasyAuthentication:
    """用于实现 JWT 认证的类。

    认证流程:
    1. 用户请求需要认证的 API，服务端返回 401 响应，要求用户提供认证信息
    2. 用户提供认证信息，服务端验证信息，并生成 JWT 令牌
        - a. * 调用 `AuthenticationHandler.load_user` 方法，返回 `UserMixin` 对象，
            若用户不存在，则抛出异常
        - b. * 调用 `AuthenticationHandler.verify_user` 方法，验证用户信息，
            若验证失败，则抛出异常
    3. 服务端返回 JWT 令牌，客户端保存该令牌，在后续请求中携带该令牌
    4. * 给路由添加使用 `require` 装饰器或添加 `current_*`依赖
    5. 服务端验证 JWT 令牌，并验证用户权限
        - a. 调用 `AuthenticationHandler.verify_token` 方法，验证 JWT 令牌,
            若验证失败，则抛出异常
        - b. 调用 `AuthenticationHandler.authenticate` 方法，验证用户权限,
            若验证失败，则抛出异常
    6. 返回响应
    """

    oauth2_scheme: Optional[OAuth2PasswordBearer] = OAuth2PasswordBearer('')

    def __init__(
        self,
        app: FastAPI,
        *,
        authentication_handler: Annotated[
            Optional[AuthenticationHandler],
            Doc(
                """
                继承自 `AuthenticationHandler` 的类，用于实现授权认证逻辑。
                """
            ),
        ] = None,
        router: Annotated[
            Optional[APIRouter],
            Doc(
                """
                用于注册认证相关路由的 `APIRouter` 对象。
                """
            ),
        ] = None,
    ):
        self.app = app
        self.config = Config()

        self.authentication_handler = authentication_handler or AuthHandler()
        self.router = router or APIRouter(prefix='', tags=['授权'])

        self.init_app(app)

    def init_app(self, app: FastAPI) -> None:
        if hasattr(app, 'easy_fastapi_authorize'):
            raise RuntimeError('一个 "EasyAuthentication" 实例已经注册到 FastAPI 应用中，请勿重复注册。')

        app.easy_fastapi_authorize = self

        binding_exception_handler(app)

        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl=self.config.easy_fastapi.authentication.token_url)

        @self.router.post(
            self.config.easy_fastapi.authentication.token_url,
            summary='获取令牌',
            description='获取令牌接口',
            response_model=APIToken)
        async def token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
            return await _async(
                self.authentication_handler.token,
                form_data,
            )

        # 由于某些原因，在此处的路由添加依赖时，会导致路由注册额外参数 self，
        # 因此重新定义一个依赖函数（self.current_jwt 可以正常注册，current_token
        # 和 current_user 会出问题）
        async def current_token(jwt: str = Depends(self.oauth2_scheme)):
            return await self.current_token(jwt)

        @self.router.post(
            self.config.easy_fastapi.authentication.refresh_url,
            summary='刷新令牌',
            description='刷新令牌接口',
            response_model=Result[APIRefresh])
        @self.require(require_refresh=True)
        async def refresh(refresh_token: Annotated[Token, Depends(current_token)]):
            return JSONResult('刷新令牌成功', data=await _async(
                self.authentication_handler.refresh,
                refresh_token,
            ))

        @self.router.post(
            self.config.easy_fastapi.authentication.login_url,
            summary='用户登录',
            description='用户登录接口',
            response_model=Result[APILogin])
        async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
            return JSONResult('登录成功', data=await _async(
                self.authentication_handler.login,
                form_data,
            ))

        @self.router.post(
            self.config.easy_fastapi.authentication.logout_url,
            summary='用户登出',
            description='用户登出接口',
            response_model=Result[None],
        )
        @self.require
        async def logout(refresh_token: str, access_token: Annotated[str, Depends(self.current_jwt)]):
            return JSONResult('登出成功', data=await _async(
                self.authentication_handler.logout,
                refresh_token,
                access_token,
            ))

        app.include_router(self.router)

    async def __require(self, token: str, scopes: list[str], require_refresh: bool):
        """验证当前请求是否有权限访问"""
        token: Token = await decode_token(token)

        if require_refresh and not token.isr:
            raise ForbiddenException('需要刷新令牌')

        if not require_refresh and token.isr:
            raise ForbiddenException('需要访问令牌')

        await _async(self.authentication_handler.authenticate, token, scopes)

    def require(self, scopes: set[str] | Callable | None = None, *, require_refresh: bool = False):
        """装饰器，用于设置 API 访问权限。

        Example:
            ```python
            from fastapi import FastAPI
            from easy_fastapi.authentication import EasyAuthentication

            app = FastAPI()
            auth = EasyAuthentication(app)

            @app.post('/logout')
            @auth.require(require_refresh=True)
            def logout():
                pass

            @app.get('/user')
            @auth.require
            def user():
                return {'message': 'Hello, user!'}

            @app.get('/admin')
            @auth.require({'admin'})
            def admin():
                return {'message': 'Hello, admin!'}
            ```

        Args:
            scopes (set[str] | Callable | None, optional): 权限列表或权限验证函数. 默认为 None.
            require_refresh (bool, optional): 是否强制使用刷新令牌. 默认为 False.
        """
        _scopes = [] if not scopes or callable(scopes) else list(scopes)

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                await self.__require(
                    kwargs.pop('__require_token'),
                    scopes=_scopes,
                    require_refresh=require_refresh,
                )
                return await _async(func, *args, **kwargs)

            # 修改函数签名
            sig = signature(func)
            new_params = [
                Parameter(
                    '__require_token',
                    Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=Annotated[str, Depends(self.oauth2_scheme)],
                )
            ] + list(sig.parameters.values())
            wrapper.__signature__ = sig.replace(parameters=new_params)
            return wrapper

        if callable(scopes):
            return decorator(scopes)
        return decorator

    async def current_jwt(self, jwt: Annotated[str, Depends(oauth2_scheme)]) -> str:
        """获取当前 JWT 令牌

        Example:
            ```python
            from fastapi import FastAPI
            from easy_fastapi.authentication import EasyAuthentication

            app = FastAPI()
            auth = EasyAuthentication(app)

            @app.get('/user')
            async def user(jwt: Annotated[str, Depends(auth.current_jwt)]):
                return {'message': 'Hello, user!', 'jwt': jwt}
            ```

        Args:
            jwt (str): JWT 令牌

        Returns:
            str: 当前 JWT 令牌
        """
        try:
            await _async(self.authentication_handler.verify_token, jwt)
        except:
            raise UnauthorizedException('JWT 令牌验证失败')

        return jwt

    async def current_token(self, jwt: Annotated[str, Depends(current_jwt)]) -> Token:
        """获取当前 JWT 令牌对应的 `Token` 对象

        Example:
            ```python
            from fastapi import FastAPI
            from easy_fastapi.authentication import EasyAuthentication, Token

            app = FastAPI()
            auth = EasyAuthentication(app)

            @app.get('/user')
            async def user(token: Annotated[Token, Depends(auth.current_token)]):
                return {'message': 'Hello, user!', 'username': token.sub}
            ```

        Args:
            jwt (str): JWT 令牌

        Returns:
            Token: 当前 JWT 令牌对应的 `Token` 对象
        """
        try:
            token = await decode_token(jwt)
        except:
            raise UnauthorizedException('JWT 令牌解析失败')

        return token

    async def current_user(self, token: Annotated[Token, Depends(current_token)]) -> UserMixin:
        """获取当前 JWT 对应的用户

        Example:
            ```python
            from fastapi import FastAPI
            from easy_fastapi.authentication import EasyAuthentication
            from app.models import User

            app = FastAPI()
            auth = EasyAuthentication(app)

            @app.get('/user')
            async def user(user: Annotated[User, Depends(auth.current_user)]):
                return {'message': 'Hello, user!', 'username': user.username}
            ```

        Args:
            token (Token): 当前 JWT 对应的 `Token` 对象

        Returns:
            UserMixin: 当前 JWT 对应的用户
        """
        return await _async(self.authentication_handler.load_user, token.sub)
