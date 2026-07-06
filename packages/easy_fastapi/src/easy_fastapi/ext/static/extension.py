"""Static 运行时扩展（StaticFiles mount）。

enabled=true 时 mount StaticFiles 到 app；enabled=false 时不 mount。
目录不存在时不报错（开发初期目录尚未创建是常见情况）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from .config import StaticConfig

if TYPE_CHECKING:
    from fastapi import FastAPI

    from easy_fastapi.core.extension import ExtensionContext


class StaticExtension:
    name = "static"
    requires: ClassVar[list[str]] = []

    def config_model(self):
        return StaticConfig

    def init_app(self, app: FastAPI, config: StaticConfig | None, ctx: ExtensionContext) -> None:
        cfg = config or StaticConfig()
        if not cfg.enabled:
            return

        from pathlib import Path

        from fastapi.staticfiles import StaticFiles

        static_dir = Path(cfg.directory)
        if not static_dir.is_absolute():
            static_dir = Path.cwd() / static_dir
        if static_dir.exists():
            app.mount(cfg.url_path, StaticFiles(directory=str(static_dir)), name="static")
            ctx.provide("static_mount", {"url_path": cfg.url_path, "directory": str(static_dir)})
