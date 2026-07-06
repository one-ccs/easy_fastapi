"""Auth 运行时扩展（工厂依赖 + provide token_service/require）。

AuthExtension 既是扩展协议实现，也是认证能力载体：
- 三级工厂依赖 current_jwt/current_token/current_user（闭包解决 self 问题）
- require 装饰器（支持 scopes 可配置校验）
- 路由注册（token/login/refresh/logout/me）
- JWT 异常全局处理器

auth 不硬依赖具体 ORM 扩展名（requires=[]），通过 ctx.require('user_model')
和 ctx.require('persistence') 动态获取服务。缺失则抛 ExtensionError。

token vs login：
- /auth/token — 标准 OAuth2 token 端点，返回原始 TokenResponse（Swagger UI /docs 用）
- /auth/login — 便捷登录端点，返回 Result[TokenResponse] 信封（API 消费者用）
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

from fastapi import APIRouter, Cookie, Depends, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from easy_fastapi.core.exceptions import ExtensionError, UnauthorizedException
from easy_fastapi.core.result import BaseResult, Result

from .config import AuthConfig
from .decorator import make_require
from .hasher import PwdlibPasswordHasher
from .schemas import AuthUserOut, TokenPayload, TokenResponse
from .token import TokenService

if TYPE_CHECKING:
    from fastapi import FastAPI

    from easy_fastapi.core.extension import ExtensionContext


def _build_blacklist_key(jti: str) -> str:
    """persistence 黑名单 key 前缀。"""
    return f"auth:blacklist:{jti}"


class AuthExtension:
    name = "auth"
    requires: ClassVar[list[str]] = []

    def __init__(self) -> None:
        # init_app 前为 None；init_app 后就绪
        self.oauth2_scheme: OAuth2PasswordBearer | None = None
        self.token_service: TokenService | None = None
        self.user_model: Any = None
        self.persistence: Any = None
        self.require: Callable | None = None
        self._user_loader: Callable[[int], Any] | None = None

    def config_model(self):
        return AuthConfig

    # ── 用户加载（默认实现 + 装饰器替换）──

    def load_user(self, func: Callable[[int], Any]) -> Callable[[int], Any]:
        """装饰器：替换默认用户加载逻辑。

        用法::

            auth = AuthExtension()

            @auth.load_user
            async def my_load_user(user_id: int):
                user = await User.get_by_id(user_id)
                await user.fetch_related("roles")
                return user

        装饰的函数完全接管加载逻辑（包括 is_active 检查等），
        需要自行处理用户不存在/已禁用等情况（抛 UnauthorizedException）。
        """
        self._user_loader = func
        return func

    async def _default_load_user(self, user_id: int) -> Any:
        """默认用户加载逻辑：按 ID 查库 + is_active 检查。"""
        user = await self.user_model.get_by_id(user_id)
        if user is None or not getattr(user, "is_active", True):
            raise UnauthorizedException("User not found or disabled")
        return user

    # ── 三级工厂依赖 ──

    def current_jwt(self) -> Callable:
        """返回闭包 dependency：提取原始 JWT 字符串（不解码）。"""

        async def dependency(jwt: str = Depends(self.oauth2_scheme)) -> str:  # noqa: B008
            if jwt is None:
                raise UnauthorizedException("Missing authentication credentials")
            return jwt

        return dependency

    def current_token(self) -> Callable:
        """返回闭包 dependency：解码 JWT + 查黑名单，返回 TokenPayload。"""

        async def dependency(jwt: str = Depends(self.current_jwt())) -> TokenPayload:  # noqa: B008
            payload = self.token_service.decode(jwt)  # 抛 PyJWT 异常 → 全局 handler
            if payload.type != "access":
                raise UnauthorizedException("Invalid access token")
            jti = payload.jti
            if jti and await self.persistence.get(_build_blacklist_key(jti)):
                raise UnauthorizedException("Token has been revoked")
            return payload

        return dependency

    def current_user(self) -> Callable:
        """返回闭包 dependency：从 TokenPayload 加载完整用户。"""

        async def dependency(token: TokenPayload = Depends(self.current_token())) -> Any:  # noqa: B008
            if token.sub is None:
                raise UnauthorizedException("Token missing user identity")
            try:
                user_id = int(token.sub)
            except (TypeError, ValueError):
                raise UnauthorizedException("Invalid token user identity") from None
            if self._user_loader is not None:
                return await self._user_loader(user_id)
            return await self._default_load_user(user_id)

        return dependency

    # ── JWT 异常全局处理器 ──

    def _register_jwt_exception_handlers(self, app: FastAPI) -> None:
        """注册 PyJWT 异常处理器，映射到细分 401 消息。"""
        from easy_fastapi.core.extras import require as req
        from easy_fastapi.core.result import ResponseResult

        jwt = req("pyjwt", "jwt")

        _www_auth = {"WWW-Authenticate": "Bearer"}

        @app.exception_handler(jwt.ExpiredSignatureError)
        async def _expired(request, exc):
            return ResponseResult.unauthorized("Token has expired", headers=_www_auth)

        @app.exception_handler(jwt.InvalidSignatureError)
        async def _invalid_sig(request, exc):
            return ResponseResult.unauthorized("Invalid signature", headers=_www_auth)

        @app.exception_handler(jwt.DecodeError)
        async def _decode_err(request, exc):
            return ResponseResult.unauthorized("Token decode failed", headers=_www_auth)

        @app.exception_handler(jwt.InvalidTokenError)
        async def _invalid_token(request, exc):
            return ResponseResult.unauthorized("Invalid access token", headers=_www_auth)

        @app.exception_handler(jwt.PyJWTError)
        async def _pyjwt_err(request, exc):
            return ResponseResult.unauthorized("Unknown token error", headers=_www_auth)

    # ── init_app ──

    def init_app(self, app: FastAPI, config: AuthConfig | None, ctx: ExtensionContext) -> None:
        if not config or not config.secret:
            raise ExtensionError("auth 扩展必须配置 secret")

        from easy_fastapi.core.protocols import Persistence, UserModelProtocol

        try:
            user_model = ctx.require("user_model", UserModelProtocol, requester="auth")
            persistence = ctx.require("persistence", Persistence, requester="auth")
        except ExtensionError:
            raise ExtensionError("auth 扩展需要先装配提供 user_model 的 ORM 扩展") from None

        # 挂到 self
        self.token_service = TokenService(
            secret=config.secret,
            algorithm=config.algorithm,
            access_expire_minutes=config.access_expire_minutes,
            refresh_expire_days=config.refresh_expire_days,
        )
        self.user_model = user_model
        self.persistence = persistence
        self.oauth2_scheme = OAuth2PasswordBearer(
            tokenUrl=f"{config.token_prefix.rstrip('/')}/token",
            auto_error=False,
        )

        # require
        self.require = make_require(self.current_user(), config.scope_match)

        # ── 构建路由 ──
        router = APIRouter(prefix=config.token_prefix)
        _cookie = config.cookie
        # cookie path 默认随 token_prefix 派生，避免用户改 token_prefix 后 cookie 不回传
        cookie_path = _cookie.path or f"{config.token_prefix.rstrip('/')}/refresh"
        _refresh_max_age = self.token_service.refresh_max_age
        _enable_refresh = config.enable_refresh
        _token_transport = config.token_transport

        def _make_token_data(user_id: str) -> tuple[TokenResponse, str | None]:
            refresh_raw = self.token_service.create_refresh_token(user_id) if _enable_refresh else None
            body_refresh = None if _token_transport == "cookie" else refresh_raw
            return TokenResponse(
                access_token=self.token_service.create_access_token(user_id),
                refresh_token=body_refresh,
            ), refresh_raw

        def _apply_refresh_cookie(response: Response, refresh_token: str | None) -> None:
            if _token_transport == "cookie" and refresh_token:
                response.set_cookie(
                    key=_cookie.name,
                    value=refresh_token,
                    max_age=_refresh_max_age,
                    path=cookie_path,
                    domain=_cookie.domain,
                    secure=_cookie.secure,
                    httponly=_cookie.httponly,
                    samesite=_cookie.samesite,
                )

        # ── 认证 + 签发 ──
        hasher = PwdlibPasswordHasher()

        async def _authenticate(form_data: OAuth2PasswordRequestForm) -> str:
            """校验用户名密码，返回 user_id 字符串；失败抛 UnauthorizedException。"""
            user = await user_model.get_by_username_or_email(form_data.username)
            if user is None or not hasher.verify(form_data.password, user.hashed_password):
                raise UnauthorizedException("Invalid username or password")
            if not getattr(user, "is_active", True):
                raise UnauthorizedException("User is disabled")
            return str(user.id)

        # ── token（标准 OAuth2 端点，Swagger UI /docs 使用）──

        @router.post("/token", response_model=TokenResponse, response_model_exclude_none=True)
        async def token(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):  # noqa: B008
            """OAuth2 password flow 令牌端点（返回原始 TokenResponse，供 Swagger UI 使用）。"""
            user_id = await _authenticate(form_data)
            token_data, refresh_raw = _make_token_data(user_id)
            _apply_refresh_cookie(response, refresh_raw)
            return token_data

        # ── login（Result 信封格式，API 消费者使用）──

        @router.post("/login", response_model=BaseResult[TokenResponse], response_model_exclude_none=True)
        async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):  # noqa: B008
            """登录（返回 Result 信封，便于业务客户端统一处理响应格式）。"""
            user_id = await _authenticate(form_data)
            token_data, refresh_raw = _make_token_data(user_id)
            _apply_refresh_cookie(response, refresh_raw)
            return Result("Login successful", data=token_data)

        # ── refresh ──
        if _enable_refresh:

            async def _validate_refresh_token(raw_token: str) -> TokenPayload:
                payload = self.token_service.decode(raw_token)  # 抛 PyJWT 异常
                if payload.type != "refresh":
                    raise UnauthorizedException("Invalid refresh token")
                jti = payload.jti
                if jti and await persistence.get(_build_blacklist_key(jti)):
                    raise UnauthorizedException("Refresh token has been revoked")
                return payload

            if _token_transport == "cookie":

                @router.post("/refresh", response_model=BaseResult[TokenResponse], response_model_exclude_none=True)
                async def refresh(
                    response: Response,
                    refresh_token: str | None = Cookie(None, alias=_cookie.name),  # noqa: B008
                ):
                    """刷新令牌（cookie 模式）。"""
                    if not refresh_token:
                        raise UnauthorizedException("Missing refresh token")
                    payload = await _validate_refresh_token(refresh_token)
                    token_data, refresh_raw = _make_token_data(payload.sub)
                    _apply_refresh_cookie(response, refresh_raw)
                    return Result("Token refreshed", data=token_data)

            else:

                @router.post("/refresh", response_model=BaseResult[TokenResponse])
                async def refresh(
                    token: str = Depends(self.current_jwt()),  # noqa: B008
                ):
                    """刷新令牌（body 模式）。"""
                    payload = await _validate_refresh_token(token)
                    token_data, _refresh_raw = _make_token_data(payload.sub)
                    return Result("Token refreshed", data=token_data)

        # ── logout ──

        @router.post("/logout", status_code=204)
        async def logout(
            response: Response,
            token_payload: TokenPayload = Depends(self.current_token()),  # noqa: B008
        ):
            """登出：将 access_token 加入黑名单，cookie 模式下清除 refresh_token cookie。"""
            if token_payload.jti:
                exp = token_payload.exp
                if exp:
                    ttl = max(int(exp - time.time()), 0)
                else:
                    # exp 缺失时用 access token 的最大有效期兜底，避免黑名单永不过期
                    ttl = self.token_service.access_max_age
                await persistence.set(_build_blacklist_key(token_payload.jti), "1", ex=ttl)
            if _token_transport == "cookie":
                response.delete_cookie(
                    key=_cookie.name,
                    path=cookie_path,
                    domain=_cookie.domain,
                    secure=_cookie.secure,
                    httponly=_cookie.httponly,
                    samesite=_cookie.samesite,
                )

        # ── me ──

        @router.get("/me", response_model=BaseResult[AuthUserOut])
        async def me(user=Depends(self.current_user())):  # noqa: B008
            """获取当前登录用户信息。"""
            return Result(data=user)

        app.include_router(router)

        # 注册 JWT 异常处理器
        self._register_jwt_exception_handlers(app)

        # provide 到 ctx
        ctx.provide("token_service", self.token_service)
        ctx.provide("require", self.require)
