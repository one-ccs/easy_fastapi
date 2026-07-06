"""项目标记（代码写入，非模板）。

.easy-fastapi.json 记录生成时的选项快照与已注册扩展，供 efa gen/db/run 判断项目状态。
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from .options import CreateOptions
from .paths import project_layout

MARKER_FILENAME = ".easy-fastapi.json"
MARKER_SCHEMA_VERSION = 1


def _derive_registered_extensions(options: CreateOptions) -> list[str]:
    """从 options 推导已注册扩展：orm→orm.*，auth/redis 直接映射。

    migration/frontend/static 不进入 registered_extensions（非扩展）。
    """
    exts: list[str] = []
    if options.orm:
        exts.append(f"orm.{options.orm}")
    if options.auth:
        exts.append("auth")
    if options.redis:
        exts.append("redis")
    return exts


def write_marker(
    project_dir: Path, options: CreateOptions, *, easy_fastapi_version: str, template_version: str
) -> Path:
    """写 .easy-fastapi.json（代码生成，不经 jinja）。返回写入路径。"""
    options_snapshot = options.model_dump()

    marker = {
        "marker_schema_version": MARKER_SCHEMA_VERSION,
        "easy_fastapi_version": easy_fastapi_version,
        "template_version": template_version,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "project_layout": project_layout(options),
        "options": options_snapshot,
        "registered_extensions": _derive_registered_extensions(options),
    }
    path = Path(project_dir) / MARKER_FILENAME
    path.write_text(json.dumps(marker, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
