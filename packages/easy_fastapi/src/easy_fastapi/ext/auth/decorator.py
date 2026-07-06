"""@require 权限装饰器。

依赖 auth 扩展提供的 current_user 闭包，检查登录状态 + scopes 权限。
支持三层配置：yaml scope_match 全局默认 + require(match=...) 逐路由覆盖 + callable 自定义。
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from inspect import Parameter, signature
from typing import Any, Literal

from fastapi import Depends

from easy_fastapi.core.exceptions import ForbiddenException, UnauthorizedException


def make_require(current_user: Callable, scope_match: Literal["any", "all"] = "any") -> Callable:
    """创建 require 装饰器工厂。

    Args:
        current_user: auth.current_user() 返回的闭包 dependency。
        scope_match: 全局默认匹配策略（"any"|"all"），来自 AuthConfig.scope_match。
    """

    def _check_scopes(required: list[str], user_scopes: list[str], match: Any) -> bool:
        """根据 match 策略判断权限。"""
        req_set = set(required)
        user_set = set(user_scopes)
        if match is None:
            match = scope_match  # 回退全局默认
        if callable(match):
            return match(req_set, user_set)  # 总是调用 callable
        if not required:
            return True  # 仅需登录
        if match == "all":
            return req_set.issubset(user_set)  # AND
        return not req_set.isdisjoint(user_set)  # any / OR（默认）

    def require(scopes: set[str] | Callable | None = None, *, match: Any = None):
        """路由权限装饰器。

        Args:
            scopes: 权限集合或被装饰函数。
                None / callable → 仅需登录。
                {'admin'} → 需要 admin 权限。
            match: 匹配策略覆盖。
                None → 用全局默认（AuthConfig.scope_match）。
                "any" → 交集（OR）。
                "all" → 子集（AND）。
                callable → 自定义 matcher：(required: set[str], user_scopes: set[str]) -> bool。
        """
        _scopes: list[str] = [] if not scopes or callable(scopes) else list(scopes)
        _match = match

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args: Any, __require_user: Any = None, **kwargs: Any):
                if __require_user is None:
                    raise UnauthorizedException()

                if _scopes or callable(_match):
                    user_scopes = getattr(__require_user, "scopes", None) or []
                    if not _check_scopes(_scopes, user_scopes, _match):
                        raise ForbiddenException()

                return await func(*args, **kwargs)

            # 注入 current_user 闭包到函数签名（追加到末尾，KEYWORD_ONLY）
            sig = signature(func)
            new_params = list(sig.parameters.values()) + [
                Parameter(
                    "__require_user",
                    Parameter.KEYWORD_ONLY,
                    default=Depends(current_user),
                )
            ]
            wrapper.__signature__ = sig.replace(parameters=new_params)
            return wrapper

        # @auth.require 无括号直接装饰函数
        if callable(scopes):
            return decorator(scopes)
        return decorator

    return require
