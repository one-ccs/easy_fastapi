"""easy_fastapi 顶层：导出 core 稳定 API 与扩展分发入口。

core 符号直接 eager import；ext 具体实现（tortoise/sqlalchemy/sqlmodel/redis
等重型可选依赖）经 get_extension(name) 按需 import，不在顶层触发。
"""

from __future__ import annotations

from .core.app import EasyFastAPI
from .core.config.loader import ConfigLoader, get_config
from .core.context import get_extension_context
from .core.exceptions import (
    ConfigError,
    EasyFastAPIError,
    ExtensionError,
    FailureException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from .core.extension import Extension, ExtensionContext
from .core.i18n import _, get_locale, set_locale
from .core.result import BaseResult, ResponseResult, Result
from .ext import get_extension

__version__ = "1.0.0"
__author__ = "one-ccs"
__email__ = "one-ccs@foxmal.com"

__all__ = [
    "EasyFastAPI",
    "get_extension_context",
    "EasyFastAPIError",
    "ExtensionError",
    "ConfigError",
    "FailureException",
    "UnauthorizedException",
    "ForbiddenException",
    "NotFoundException",
    "Extension",
    "ExtensionContext",
    "ConfigLoader",
    "get_config",
    "_",
    "get_locale",
    "set_locale",
    "BaseResult",
    "Result",
    "ResponseResult",
    "get_extension",
    "__version__",
]
