#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Annotated, Final, Optional, Callable, Sequence
from typing_extensions import Doc
from collections import abc
from datetime import datetime
from functools import wraps
from inspect import Parameter, iscoroutinefunction, signature

import bcrypt
from starlette.requests import HTTPConnection
from starlette.responses import Response
from starlette.authentication import (
    AuthenticationBackend,
    AuthCredentials,
    AuthenticationError,
    BaseUser,
)
from starlette.middleware.authentication import AuthenticationMiddleware
from fastapi import (
    FastAPI,
    Depends,
)
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
from pydantic import (
    BaseModel,
    computed_field,
)
from jwt import (
    ExpiredSignatureError,
    InvalidSignatureError,
    DecodeError,
    InvalidTokenError,
    PyJWTError,
    decode as decode_jwt,
    encode as encode_jwt,
)
from easy_pyoc import (
    DateTimeUtil,
    Magic,
)

from ..exception import (
    UnauthorizedException,
    ForbiddenException,
)
from ..config import Config
from ..result import (
    JSONResponseResult,
    Result,
)


AUTH_HEADER_NAME: Final[str] = 'Authorization'
AUTH_TYPE: Final[str] = 'Bearer'


class Token(Magic, BaseModel):
    """Token 数据类，将 JWT 令牌解析为 Token 数据类"""

    # 是否是刷新令牌
    isr: bool = False
    # 权限列表
    sco: list[str] | None = None
    # 用户唯一标识或用户信息
    sub: str | dict
    # 过期时间
    exp: datetime
    # 发行者
    iss: str | None = None
    # 接收者
    aud: str | None = None
    # 签发时间
    iat: datetime | None = None
    # 生效时间
    nbf: datetime | None = None
    # JWT 唯一标识
    jti: str | None = None


class TokenUser(Magic, BaseUser):
    """Token 用户类，将 Token 信息转换为用户信息"""

    def __init__(self, token: Token) -> None:
        if not isinstance(token, Token):
            raise TypeError('token 必须是 Token 类型')

        self.token = token
        self.username = token.sub if isinstance(token.sub, str) else token.sub.get('username')
        self.credentials = AuthCredentials(token.sco)

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.username

    def get_authenticate(self) -> Optional[tuple[AuthCredentials, 'TokenUser']]:
        return self.credentials, self

    def has_permission(self, credentials: Optional[AuthCredentials | Sequence[str]]) -> bool:
        """判断当前用户是否有指定的权限

        Args:
            credentials (Optional[AuthCredentials | Sequence[str]]): 用户凭据，当为 None 时返回 True

        Returns:
            bool: 是否有权限
        """
        if credentials is None:
            return True
        if isinstance(credentials, abc.Sequence):
            return set(self.credentials.scopes).issuperset(set(credentials))
        if isinstance(credentials, set):
            return set(self.credentials.scopes).issuperset(credentials)
        return set(self.credentials.scopes).isdisjoint(set(credentials.scopes))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TokenUser):
            return False
        return self.username == other.username


class UserMixin(Magic, BaseModel):
    """用户基类，期望由用户实体类继承，并实现 `roles` 计算属性"""
    username: str

    @computed_field
    @property
    def roles(self) -> Optional[list[str]]:
        """用户角色列表"""
        raise NotImplementedError()


class APIToken(BaseModel):
    token_type: str
    access_token: str
    refresh_token: str


class APILogin(BaseModel):
    user: UserMixin
    token_type: str
    access_token: str
    refresh_token: str


class APIRefresh(BaseModel):
    token_type: str
    access_token: str


class AuthorizeBackend(AuthenticationBackend):

    def __init__(self, auth_app: 'EasyFastAPIAuthorize'):
        self.auth_app = auth_app

    async def authenticate(self, request: HTTPConnection) -> Optional[tuple[AuthCredentials, TokenUser]]:
        if AUTH_HEADER_NAME not in request.headers:
            return None
        if request.url.path == self.auth_app.config.easy_fastapi.authorize.token_url:
            return None

        auth = request.headers[AUTH_HEADER_NAME]
        scheme, jwt = auth.split()

        if scheme != AUTH_TYPE:
            raise AuthenticationError(UnauthorizedException('无效的认证类型'))

        try:
            if self.auth_app.verify_token_handler is not None:
                await _async(self.auth_app.verify_token_handler, jwt)

            token = await decode_token(jwt)
        except ExpiredSignatureError:
            raise AuthenticationError(ExpiredSignatureError('令牌已过期'))
        except InvalidSignatureError:
            raise AuthenticationError(InvalidSignatureError('无效的签名'))
        except DecodeError:
            raise AuthenticationError(DecodeError('令牌解析失败'))
        except InvalidTokenError:
            raise AuthenticationError(InvalidTokenError('无效的访问令牌'))
        except Exception as exc:
            raise AuthenticationError(exc)

        return TokenUser(token).get_authenticate()


class AuthorizeHandler:
    def __init__(self, auth_app: 'EasyFastAPIAuthorize'):
        self.auth_app = auth_app

    async def __login(self, form_data: OAuth2PasswordRequestForm) -> tuple[UserMixin, str, str]:
        if self.load_user_handler is None:
            raise RuntimeError('请使用 "EasyFastAPIAuthorize.load_user" 装饰器设置 "load_user_handler" 处理器')
        if self.verify_user_handler is None:
            raise RuntimeError('请使用 "EasyFastAPIAuthorize.verify_user" 装饰器设置 "verify_user_handler" 处理器')

        db_user: UserMixin = await _async(self.load_user_handler, form_data.username)

        await _async(self.verify_user_handler, form_data, db_user)

        access_token = await create_access_token(sub=db_user.username, sco=db_user.roles)
        refresh_token = await create_refresh_token(sub=db_user.username, sco=db_user.roles)

        return db_user, access_token, refresh_token

    async def token(self, form_data: OAuth2PasswordRequestForm) -> APIToken:
        _, access_token, refresh_token = await self.__login(form_data)
        return APIToken(
            token_type=AUTH_TYPE,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def login(self, form_data: OAuth2PasswordRequestForm) -> APILogin:
        db_user, access_token, refresh_token = await self.__login(form_data)
        return APILogin(
            user=db_user,
            token_type=AUTH_TYPE,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh(self, refresh_token: str):
        raise NotImplementedError()

    async def logout(self):
        raise NotImplementedError()

    async def register(self, user: UserMixin):
        raise NotImplementedError()


class EasyFastAPIAuthorize:
    """用于实现 JWT 认证的类。

    认证流程:
        1. 用户请求需要认证的 API，服务端返回 401 响应，要求用户提供认证信息
        2. 用户提供认证信息，服务端验证信息，并生成 JWT 令牌
            a. * 使用 `load_user` 装饰器，设置 `load_user_handler` 处理器返回 `UserMixin` 对象
            b. * 使用 `verify_user` 装饰器，设置 `verify_user_handler` 处理器验证用户信息
            c. 若用户信息验证成功，则生成 JWT 令牌（包含权限列表），并返回；否则，返回 400 响应
        3. 服务端返回 JWT 令牌，客户端保存该令牌，在后续请求中携带该令牌
        4. 服务端验证 JWT 令牌，并获取用户信息
            a. 使用 `verify_token` 装饰器，设置 `verify_token_handler` 处理器验证 JWT 令牌
            b. 使用 `authorization` 装饰器, 设置 `authorization_handler` 处理器验证用户权限
            c. * 使用 `require` 装饰器，给路由添加权限控制
            d. 若令牌有效且用户拥有访问权限，则返回 API 响应；否则，返回 403 响应
        5. 服务端根据用户信息，判断用户是否有权限访问该 API
        6. 若用户有权限访问，则返回 API 响应；否则，返回 403 响应
    """

    oauth2_scheme: Optional[OAuth2PasswordBearer] = OAuth2PasswordBearer('')

    def __init__(
        self,
        app: FastAPI,
        authorize_backend: Annotated[
            Optional[AuthenticationBackend],
            Doc(
                """
                继承自 `starlette.authentication.AuthenticationBackend` 的类，
                用于实现 JWT 认证逻辑。默认使用 `AuthorizeBackend` 类
                """
            ),
        ] = None,
        authorize_handler: Annotated[
            Optional[AuthorizeHandler],
            Doc(
                """
                继承自 `AuthorizeHandler` 的类，用于实现授权认证逻辑。
                默认使用 `AuthorizeHandler` 类
                """
            ),
        ] = None,
    ):
        self.app = app
        self.config = Config()

        self._authorize_backend = authorize_backend or AuthorizeBackend(self)
        self._authorize_handler = authorize_handler or AuthorizeHandler(self)

        self._on_error: Optional[Callable[[HTTPConnection, AuthenticationError], Response]] = None
        self._load_user: Optional[Callable[[str], UserMixin]] = None
        self._verify_user: Optional[Callable[[OAuth2PasswordRequestForm, UserMixin], None]] = None
        self._verify_token: Optional[Callable[[str], None]] = None
        self._authorization: Optional[Callable[[TokenUser, AuthCredentials], None]] = None

        self.init_app(app)

    def init_app(self, app: FastAPI) -> None:
        if hasattr(app, 'easy_fastapi_authorize'):
            raise RuntimeError('一个 "EasyFastAPIAuthorize" 实例已经注册到 FastAPI 应用中，请勿重复注册。')

        app.easy_fastapi_authorize = self

        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl=self.config.easy_fastapi.authorize.token_url)

        self.app.add_middleware(
            AuthenticationMiddleware,
            backend=self.authorize_backend,
            on_error=self.__on_error,
        )

        @app.post(self.config.easy_fastapi.authorize.token_url,
            tags=['授权'],
            summary='获取令牌',
            description='获取令牌接口',
            response_model=APIToken)
        async def token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
            return _async(self.authorize_handler.token, form_data)

        @app.post(self.config.easy_fastapi.authorize.login_url,
            tags=['授权'],
            summary='用户登录',
            description='用户登录接口',
            response_model=Result.of(APILogin))
        async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
            return Result('登录成功', data=await _async(self.authorize_handler.login, form_data))

        @app.post(self.config.easy_fastapi.authorize.refresh_url,
            tags=['授权'],
            summary='刷新令牌',
            description='刷新令牌接口',
            response_model=APIRefresh)
        @self.require(force_refresh=True)
        async def refresh(token: TokenUser = Depends(self.current_token)):
            access_token = await create_access_token(sub=token.token.sub, sco=token.token.sco)
            return Result('刷新令牌成功', data=APIRefresh(
                token_type=AUTH_TYPE,
                access_token=access_token,
            ))

    @property
    def authorize_backend(self) -> AuthenticationBackend:
        """获取 `AuthenticationBackend` 对象"""
        return self._authorize_backend

    @property
    def authorize_handler(self) -> AuthorizeHandler:
        """获取 `AuthorizeHandler` 对象"""
        return self._authorize_handler

    def __on_error(self, request: HTTPConnection, exc: AuthenticationError) -> Response:
        """当 `AuthenticationMiddleware` 抛出 `AuthenticationError` 异常时调用。
        由于该异常无法由 FastAPI 捕获，因此需要手动调用对应的异常处理器。
        """
        if self._on_error is not None:
            return self._on_error(request, exc)

        sub_exc = exc.args[0]

        if isinstance(sub_exc, PyJWTError) or isinstance(sub_exc, UnauthorizedException):
            return JSONResponseResult.unauthorized(str(exc))

        return JSONResponseResult.failure_with_id(str(exc), exc=exc, code=401)

    def on_error(self, handler: Callable[[HTTPConnection, AuthenticationError], Response]) -> None:
        """装饰器，用于设置认证失败时的处理器。该处理器应接收 `HTTPConnection` 和
        `AuthenticationError` 作为参数，并返回一个 `Response` 对象。

        注：若异常处理器已注册到 `FastAPI` 应用中，则该处理器将不会被调用。

        Example:
            ```python
            from fastapi import FastAPI
            from easy_fastapi import EasyFastAPIAuthorize

            app = FastAPI()
            auth = EasyFastAPIAuthorize(app)

            @auth.on_error
            def on_error(request: HTTPConnection, exc: AuthenticationError) -> Response:
                return JSONResponseResult.failure_with_id(str(exc), exc=exc, code=401)
            ```

        Args:
            handler (Callable[[HTTPConnection, AuthenticationError], Response]): 处理器
        """
        self._on_error = handler

    @property
    def on_error_handler(self):
        """获取由 `on_error` 设置的处理器"""
        return self._on_error

    def load_user(self, handler: Callable[[str], UserMixin]) -> None:
        """装饰器，用于设置加载用户时的处理器。该处理器应接收用户 ID (`str`) 作为参数，
        并返回一个 `UserMixin` 对象。若用户不存在，应抛出 `NotFoundException` 异常。

        Example:
            ```python
            from fastapi import FastAPI
            from easy_fastapi import EasyFastAPIAuthorize
            from app.models import User

            app = FastAPI()
            auth = EasyFastAPIAuthorize(app)

            @auth.load_user
            def load_user(id: str) -> User:
                # 假设这里有一个数据库查询函数，返回一个 User 对象
                user = User.by_id(id)
                if not user:
                    raise NotFoundException('用户不存在')
                return user
            ```

        Args:
            handler (Callable[[str], UserMixin]): 处理器
        """
        self._load_user = handler

    @property
    def load_user_handler(self):
        """获取由 `load_user` 设置的处理器"""
        return self._load_user

    def verify_user(self, handler: Callable[[OAuth2PasswordRequestForm, UserMixin], None]) -> None:
        """装饰器，用于设置验证用户登录信息时的处理器。该处理器应接收 `UserMixin` 对象和
        `OAuth2PasswordRequestForm` 对象作为参数，验证失败时应抛出异常。

        Example:
            ```python
            from fastapi import FastAPI
            from easy_fastapi import EasyFastAPIAuthorize
            from app.models import User

            app = FastAPI()
            auth = EasyFastAPIAuthorize(app)

            @auth.verify_user
            async def verify_user(form_data: OAuth2PasswordRequestForm, user: User):
                if not await verify_password(form_data.password, user.hashed_password):
                    raise UnauthorizedException('密码错误')
            ```

        Args:
            handler (Callable[[OAuth2PasswordRequestForm, UserMixin], None]): 处理器
        """
        self._verify_user = handler

    @property
    def verify_user_handler(self):
        """获取由 `verify_user` 设置的处理器"""
        return self._verify_user

    def verify_token(self, handler: Callable[[str], None]) -> None:
        """装饰器，用于设置验证 JWT 令牌时的处理器。该处理器应接收 JWT 令牌 (`str`)
        作为参数，若验证失败应抛出异常。

        Example:
            ```python
            from fastapi import FastAPI
            from easy_fastapi import EasyFastAPIAuthorize

            app = FastAPI()
            auth = EasyFastAPIAuthorize(app)

            @auth.verify_token
            def verify_token(token: str):
                # 假设这里有一个令牌验证函数，返回一个 bool 值
                if is_token_revoked(token):
                    raise ForbiddenException('令牌已销毁')
            ```

        Args:
            handler (Callable[[str], None]): 处理器
        """
        self._verify_token = handler

    @property
    def verify_token_handler(self):
        """获取由 `verify_token` 设置的处理器"""
        return self._verify_token

    def authorization(self, handler: Callable[[TokenUser, AuthCredentials], None]) -> None:
        """装饰器，用于设置验证用户权限时的处理器。该处理器应接收 `TokenUser` 对象和
        `AuthCredentials` 对象作为参数，若验证失败应抛出 `ForbiddenException` 异常。

        Example:
            ```python
            from fastapi import FastAPI
            from easy_fastapi import EasyFastAPIAuthorize

            app = FastAPI()
            auth = EasyFastAPIAuthorize(app)

            @auth.authorization
            def authorization(user: TokenUser, credentials: AuthCredentials):
                if not user.has_permission(credentials):
                    raise ForbiddenException('无访问权限')
            ```

        Args:
            handler (Callable[[TokenUser, AuthCredentials], None]): 处理器
        """
        self._authorization = handler

    @property
    def authorization_handler(self):
        """获取由 `authorization` 设置的处理器"""
        return self._authorization

    async def __require(self, token: str, scopes: list[str], force_refresh: bool):
        """验证当前请求是否有权限访问"""
        token_user = TokenUser(await decode_token(token))

        if force_refresh and not token_user.token.isr:
            raise ForbiddenException('请使用刷新令牌')

        if self.authorization_handler is not None:
            await _async(self.authorization_handler, token_user, AuthCredentials(scopes))
            return

        if not token_user.has_permission(scopes):
            raise ForbiddenException('无访问权限')

    def require(self, scopes: set[str] | Callable | None = None, *, force_refresh: bool = False):
        """装饰器，用于设置 API 访问权限。

        Example:
            ```python
            from fastapi import FastAPI
            from easy_fastapi import EasyFastAPIAuthorize

            app = FastAPI()
            auth = EasyFastAPIAuthorize(app)

            @app.post('/logout')
            @auth.require(force_refresh=True)
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
            force_refresh (bool, optional): 是否强制使用刷新令牌. 默认为 False.
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                _scopes = [] if callable(scopes) or None else list(scopes)
                __require_token = kwargs.pop('__require_token')
                await self.__require(__require_token, scopes=_scopes, force_refresh=force_refresh)
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

    async def current_token(self, jwt: Annotated[str, Depends(oauth2_scheme)]) -> TokenUser:
        """获取当前 JWT 令牌对应的 `TokenUser` 对象

        Example:
            ```python
            from fastapi import FastAPI
            from easy_fastapi import EasyFastAPIAuthorize, TokenUser

            app = FastAPI()
            auth = EasyFastAPIAuthorize(app)

            @app.get('/user')
            async def user(token_user: Annotated[TokenUser, Depends(auth.current_token)]):
                return {'message': 'Hello, user!', 'username': token_user.username}
            ```

        Args:
            jwt (str): JWT 令牌

        Returns:
            TokenUser: 当前 JWT 令牌对应的 `TokenUser` 对象
        """
        if self.verify_token_handler is not None:
            try:
                await _async(self.verify_token_handler, jwt)
            except:
                raise UnauthorizedException('JWT 令牌验证失败')

        try:
            token = await decode_token(jwt)
        except:
            raise UnauthorizedException('JWT 令牌解析失败')

        return TokenUser(token)

    async def current_user(self, token_user: Annotated[TokenUser, Depends(current_token)]) -> UserMixin:
        """获取当前 JWT 对应的用户

        Example:
            ```python
            from fastapi import FastAPI
            from easy_fastapi import EasyFastAPIAuthorize
            from app.models import User

            app = FastAPI()
            auth = EasyFastAPIAuthorize(app)

            @app.get('/user')
            async def user(user: Annotated[User, Depends(auth.current_user)]):
                return {'message': 'Hello, user!', 'username': user.username}
            ```

        Args:
            token_user (TokenUser): 当前 JWT 对应的 `TokenUser` 对象

        Returns:
            UserMixin: 当前 JWT 对应的用户
        """
        if self.load_user_handler is None:
            raise RuntimeError('请使用 "EasyFastAPIAuthorize.load_user" 装饰器设置 "load_user_handler" 处理器')

        return await _async(self.load_user_handler, token_user.username)


async def _async(func: Callable, *args, **kwargs):
    """以异步方式调用同步函数"""
    if iscoroutinefunction(func):
        return await func(*args, **kwargs)
    return func(*args, **kwargs)


async def encrypt_password(password: str) -> str:
    """返回加密后的密码

    Args:
        password (str): 明文密码

    Returns:
        str: 加密后的密码
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否正确

    Args:
        plain_password (str): 明文密码
        hashed_password (str): 加密后的密码

    Returns:
        bool: 密码是否正确
    """
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


async def create_access_token(
    *,
    sub: str,
    sco: list[str] | None = None,
    iat: datetime = DateTimeUtil.now(),
) -> str:
    """创建访问令牌

    Args:
        sub (str): 用户名
        sco (list[str], optional): 权限列表. 默认为 None.
        iss (str, optional): 发行者. 默认为 None.
        iat (datetime, optional): 签发时间. 默认为 DateTimeUtil.now().

    Returns:
        str: 访问令牌
    """
    config = Config()

    expire = DateTimeUtil.now() + config.easy_fastapi.authorize.access_token_expire_minutes
    iss = config.easy_fastapi.authorize.iss
    to_encode = {'sub': sub, 'sco': sco, 'exp': expire, 'iss': iss, 'iat': iat, 'isr': False}
    encoded_jwt = encode_jwt(
        to_encode,
        config.easy_fastapi.authorize.secret_key,
        config.easy_fastapi.authorize.algorithm,
    )
    return encoded_jwt


async def create_refresh_token(
    *,
    sub: str,
    sco: list[str] | None = None,
    iat: datetime = DateTimeUtil.now(),
) -> str:
    """创建刷新令牌

    Args:
        sub (str): 用户名
        sco (list[str], optional): 权限列表. 默认为 None.
        iat (datetime, optional): 签发时间. 默认为 DateTimeUtil.now().

    Returns:
        str: 刷新令牌
    """
    config = Config()

    expire = DateTimeUtil.now() + config.easy_fastapi.authorize.refresh_token_expire_minutes
    iss = config.easy_fastapi.authorize.iss
    to_encode = {'sub': sub, 'sco': sco, 'exp': expire, 'iss': iss, 'iat': iat, 'isr': True}
    encoded_jwt = encode_jwt(
        to_encode,
        config.easy_fastapi.authorize.secret_key,
        config.easy_fastapi.authorize.algorithm,
    )
    return encoded_jwt


async def decode_token(token: str) -> Token:
    """解析令牌为字典，若令牌无效将引发错误

    Args:
        token (str): 令牌

    Returns:
        Token: 令牌数据
    """
    config = Config()

    payload = decode_jwt(
        token,
        config.easy_fastapi.authorize.secret_key,
        algorithms=[
            config.easy_fastapi.authorize.algorithm,
        ],
    )

    return Token(**payload)
