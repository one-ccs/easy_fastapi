"""easy_fastapi 运行时扩展层。

ext 放具体实现（ORM/migration/auth/redis），按需经 use() 装配。
core 不 import ext；ext 依赖 core 协议。

get_extension：按名返回扩展实例（供生成项目 main.py 装配）。
懒加载：避免顶层 import 触发真实 ORM 依赖（core 保持零可选依赖）。
"""

from __future__ import annotations

from easy_fastapi.core.exceptions import ExtensionError


def get_extension(name: str):
    if name == "orm.tortoise":
        from .orm.tortoise.extension import TortoiseExtension

        return TortoiseExtension()
    if name == "orm.sqlalchemy":
        from .orm.sqlalchemy.extension import SQLAlchemyExtension

        return SQLAlchemyExtension()
    if name == "orm.sqlmodel":
        from .orm.sqlmodel.extension import SQLModelExtension

        return SQLModelExtension()
    if name == "auth":
        from .auth.extension import AuthExtension

        return AuthExtension()
    if name == "redis":
        from .redis.extension import RedisExtension

        return RedisExtension()
    if name == "static":
        from .static.extension import StaticExtension

        return StaticExtension()
    if name == "i18n":
        from .i18n.extension import I18nExtension

        return I18nExtension()
    raise ExtensionError(f"未知扩展 '{name}'")
