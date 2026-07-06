"""项目语义解析共享层（CLI 与 Core 共用）。

提供 find_project_root / resolve_config_path / read_marker / resolve_db_config / app_target，
供 CLI 薄壳（项目发现）和 Core 命令（执行逻辑）共用。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from easy_fastapi.core.exceptions import ConfigError

MARKER_FILENAME = ".easy-fastapi.json"

_VALID_ORMS: frozenset[str] = frozenset({"tortoise", "sqlalchemy", "sqlmodel"})


def find_project_root(start: Path | None = None) -> Path:
    """检查 start（默认 CWD）是否为 Easy FastAPI 项目根目录。

    要求 start 下存在 .easy-fastapi.json，否则报错——
    禁止在非项目根目录启动。
    """
    directory = Path(start) if start is not None else Path.cwd()
    if not (directory / MARKER_FILENAME).exists():
        raise ConfigError(
            f"当前目录不是 Easy FastAPI 项目（缺少 {MARKER_FILENAME}）。"
            f"请在项目根目录启动，或先用 efa create 创建项目。"
        )
    return directory


def resolve_config_path(start: Path | None = None) -> Path:
    """从项目根目录推导 easy-fastapi.yaml 路径。

    先 find_project_root 确认 CWD 是项目根，再读 marker 中 project_layout
    推导 yaml 位置：
    - backend-only: project_root/easy-fastapi.yaml
    - fullstack: project_root/backend/easy-fastapi.yaml
    """
    root = find_project_root(start)
    # find_project_root 已确认 marker 存在，直接读取
    marker = _read_marker_unchecked(root)
    _, app_dir_rel = app_target(marker)
    yaml_path = (root / app_dir_rel / "easy-fastapi.yaml") if app_dir_rel else (root / "easy-fastapi.yaml")
    if not yaml_path.exists():
        raise ConfigError(f"配置文件 '{yaml_path}' 不存在。脚手架生成的项目必须包含 easy-fastapi.yaml。")
    return yaml_path


def read_marker(project_dir: Path) -> dict:
    """读 .easy-fastapi.json。缺失/损坏报 ConfigError。"""
    path = Path(project_dir) / MARKER_FILENAME
    if not path.exists():
        raise ConfigError(
            f"当前目录不是 Easy FastAPI 项目（缺少 {MARKER_FILENAME}）。"
            f"请在项目根目录执行该命令，或先用 efa create 创建。"
        )
    return _read_marker_unchecked(project_dir)


def _read_marker_unchecked(project_dir: Path) -> dict:
    """读 .easy-fastapi.json（不检查存在性，由调用方保证）。损坏报 ConfigError。"""
    path = Path(project_dir) / MARKER_FILENAME
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"{MARKER_FILENAME} 损坏（非法 JSON）：{e}") from e


def app_target(marker: dict) -> tuple[str, str | None]:
    """按 project_layout 选 uvicorn 的 (import 字符串, app_dir)。

    fullstack → ("app.main:app", "backend")
    backend-only / 缺省 → ("app.main:app", None)
    """
    if marker.get("project_layout") == "fullstack":
        return "app.main:app", "backend"
    return "app.main:app", None


def app_target_from_dir(project_dir: Path) -> tuple[str, str | None]:
    """便捷封装：从项目目录读 marker → 推导 app_target。"""
    marker = read_marker(project_dir)
    return app_target(marker)


def resolve_app_dir(project_root: Path, marker: dict) -> Path:
    """根据 project_layout 返回应用目录（app 代码所在目录）。

    fullstack → project_root/backend
    backend-only / 缺省 → project_root

    所有需要推导 "项目 app 目录" 的地方应统一调用此函数，
    避免各自重复 marker["project_layout"] 判断逻辑。
    """
    _, app_dir_rel = app_target(marker)
    return (project_root / app_dir_rel) if app_dir_rel else project_root


def resolve_app_dir_from_config(config_path: Path) -> Path:
    """从 easy-fastapi.yaml 路径反推应用目录。

    fullstack: project_root/backend/easy-fastapi.yaml → project_root/backend
    backend-only: project_root/easy-fastapi.yaml → project_root

    适用于运行时（EasyFastAPI 已加载配置，ConfigLoader.path 可用），
    无需再读 marker 文件。与 resolve_app_dir 保持一致的推导规则。
    """
    return config_path.parent


def resolve_db_config(project_dir: Path) -> tuple[str, str, list[str], Path]:
    """读 marker 取 orm + 读 yaml 取 db 配置 → 构建真实 db_url。

    返回 (orm, db_url, models, app_dir)。
    复用 resolve_config_path 定位 yaml，不再手动推导路径。
    """
    from easy_fastapi.core.config.loader import get_config
    from easy_fastapi.ext.orm.base.db_config import OrmName, build_db_url

    marker = read_marker(project_dir)
    options = marker.get("options", {})
    if not options.get("database", False):
        raise ConfigError("当前项目未启用数据库")
    orm = options.get("orm")
    if not orm:
        raise ConfigError("当前项目未启用 ORM")
    if orm not in _VALID_ORMS:
        raise ConfigError(f"不支持的 ORM 类型：'{orm}'（仅支持 tortoise/sqlalchemy/sqlmodel）")
    app_dir = resolve_app_dir(project_root=project_dir, marker=marker)
    yaml_path = resolve_config_path(project_dir)
    loader = get_config(yaml_path)
    db_url = build_db_url(cast("OrmName", orm), loader)
    return orm, db_url, ["app.models"], app_dir
