"""扩展协议 + ExtensionContext。

Extension v1 协议：config_model() + init_app(app, config, ctx)。
无 on_post_start——config 加载由框架在 use() 内统一做，扩展不在 init_app 里临时读配置。

ExtensionContext：扩展间唯一合法共享面，提供 has/get_config/provide/require。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Protocol, runtime_checkable

from pydantic import BaseModel

from .exceptions import ExtensionError

if TYPE_CHECKING:
    from fastapi import FastAPI

    from .config.loader import ConfigLoader


@runtime_checkable
class Extension(Protocol):
    """运行时扩展协议。

    name: 唯一标识（也作为 ctx 扩展注册表 key）。
    config_section: YAML 配置段名（默认等于 name，用于 loader.section("easy_fastapi.<config_section>")）。
        当 name 含点（如 orm.sqlalchemy）但配置位于不同段（如 database）时需覆盖。
        未声明时框架默认使用 name。
    requires: 硬依赖的具体扩展名（极少用；一般用 ctx.require 服务依赖）。
    """

    name: str
    requires: ClassVar[list[str]]

    def config_model(self) -> type[BaseModel] | None:
        """声明配置类型，无副作用。返回 None 表示该扩展无配置段。"""
        ...

    def init_app(
        self,
        app: FastAPI,
        config: BaseModel | None,
        ctx: ExtensionContext,
    ) -> None:
        """注册能力，消费框架已加载的 config。"""
        ...


class ExtensionContext:
    """扩展间唯一合法共享面。

    extensions: 已注册扩展实例。
    configs: 各扩展已加载的配置（由 use() 内部 loader.section 填充）。
    services: 扩展间共享的服务（ctx.provide/require）。
    """

    def __init__(self) -> None:
        self.extensions: dict[str, Extension] = {}
        self.configs: dict[str, BaseModel | None] = {}
        self.services: dict[str, Any] = {}
        self._loader: ConfigLoader | None = None  # ConfigLoader，由 EasyFastAPI 装配时注入

    def set_loader(self, loader: ConfigLoader) -> None:
        """注入 ConfigLoader（由 EasyFastAPI.__init__ 调用）。"""
        self._loader = loader

    def get_loader(self) -> ConfigLoader | None:
        """取回 ConfigLoader（扩展可用它读任意配置段）。"""
        return self._loader

    def has(self, name: str) -> bool:
        """扩展是否已注册。"""
        return name in self.extensions

    def get_config(self, name: str) -> BaseModel | None:
        """取已加载配置；扩展未注册或无配置段返回 None。"""
        return self.configs.get(name)

    def provide(self, key: str, value: Any, *, override: bool = False) -> None:
        """注册服务。默认禁止重复 key；覆盖须 override=True。

        redis 覆盖 persistence 是明确允许特例（redis use 时 enabled=True 用 override）。
        """
        if key in self.services and not override:
            raise ExtensionError(f"service '{key}' 已注册，重复 provide 须显式 override=True")
        self.services[key] = value

    def require(self, key: str, type_: type, *, requester: str | None = None) -> Any:
        """取服务并运行时校验。

        缺失/类型不符 → ExtensionError，含 service key + 发起扩展名 + 补救提示。
        运行时校验仅针对可 isinstance 判定的具体类或 @runtime_checkable Protocol。
        """
        if key not in self.services:
            who = f"扩展 '{requester}' " if requester else ""
            raise ExtensionError(f"{who}需要 service '{key}'，但当前上下文未提供。请先 use() 提供该能力的扩展。")
        value = self.services[key]
        # 运行时类型校验：仅针对可校验类型（不可校验的普通 Protocol/TypeVar 跳过强校验）
        try:
            ok = isinstance(value, type_)
        except TypeError:
            ok = True
        if not ok:
            raise ExtensionError(
                f"service '{key}' 类型不符：期望 {getattr(type_, '__name__', type_)}，实际 {type(value).__name__}。"
            )
        return value
