"""aerich 迁移实现（Tortoise）。

init（非幂等）/ migrate / upgrade。aerich 命令为 async API。
sync 对 Tortoise 无意义（用 generate_schemas，由 db_ops 直接调）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from easy_fastapi.core.extras import require

from .base import MigrationOp

# 模块级 Command 引用：真实来自 aerich；测试可用 monkeypatch 替换。
_aerich = require("aerich", "aerich")
Command = _aerich.Command


def _is_initialized() -> bool:
    """aerich 以 pyproject.toml 含 [tool.aerich] 段标记已初始化。"""
    p = Path("pyproject.toml")
    if not p.exists():
        return False
    return "[tool.aerich]" in p.read_text(encoding="utf-8")


def _build_config(db_url: str | None, models: list[str] | None) -> dict[str, Any]:
    return {
        "connections": {"default": db_url or "sqlite://db.sqlite"},
        "apps": {
            "models": {
                "models": ["aerich.models"] + (models or []),
                "default_connection": "default",
            }
        },
        "use_tz": False,
        "timezone": "Asia/Chongqing",
    }


async def run(app: Any, op: MigrationOp, *, db_url: str | None = None, models: list[str] | None = None):
    if op not in ("init", "migrate", "upgrade"):
        raise ValueError(f"aerich 不支持的操作 '{op}'（仅 init/migrate/upgrade）")

    cmd = Command(
        tortoise_config=_build_config(db_url, models),
        app="models",
        location="./migrations",
    )

    if op == "init":
        if _is_initialized():
            raise RuntimeError("aerich 已初始化（init 非幂等，请勿重复执行）")
        await cmd.init()
        return
    # migrate/upgrade 需要 Migrate 类状态（migrate_location 等），必须先 init。
    # aerich Command.migrate 内部调 Migrate.migrate，依赖 Migrate.init 设置的类变量。
    await cmd.init()
    if op == "migrate":
        await cmd.migrate()
        return
    if op == "upgrade":
        await cmd.upgrade()
        return
