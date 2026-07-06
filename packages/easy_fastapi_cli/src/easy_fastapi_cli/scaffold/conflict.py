"""create 冲突策略。

- efa create NAME：目标必须不存在或为空
- efa create .（in_place）：允许白名单文件共存，其余存在则报错

检查结果以 ConflictResult 返回，由调用方决定提示语气与是否继续：
- empty：目录空，可直接创建
- whitelist_only：仅白名单条目，警告并询问用户是否继续
- blocked：含非白名单条目，禁止创建
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

# in_place 模式允许预先存在的条目（不视为冲突）
WHITELIST_IN_PLACE = {
    ".git",
    ".gitignore",
    ".easy-fastapi.json",
    ".venv",
    ".python-version",
    "LICENSE",
    "main.py",
    "README.md",
    "pyproject.toml",
    "uv.lock",
}

# 冲突状态：empty=空目录 / whitelist_only=仅白名单 / blocked=含非白名单
ConflictStatus = Literal["empty", "whitelist_only", "blocked"]


class ConflictResult(BaseModel):
    """check_target 的检查结果。

    status: empty / whitelist_only / blocked
    offenders: 非白名单条目名列表（blocked 时非空）
    whitelisted: 命中白名单的条目名列表（whitelist_only 时非空）
    """

    status: ConflictStatus
    offenders: list[str] = []
    whitelisted: list[str] = []


def check_target(target_dir: Path, *, in_place: bool) -> ConflictResult:
    """检查目标目录，返回 ConflictResult（不抛异常）。

    非空目录需用户确认：
    - in_place 模式且仅白名单条目 → whitelist_only（警告，询问是否继续）
    - in_place 模式且含非白名单条目 → blocked（禁止）
    - 非 in_place 模式且目录非空 → blocked（禁止）
    """
    target_dir = Path(target_dir)
    if not target_dir.exists() or not any(target_dir.iterdir()):
        return ConflictResult(status="empty")

    entries = [p.name for p in target_dir.iterdir()]
    if not in_place:
        # efa create NAME：非空即禁止
        return ConflictResult(status="blocked", offenders=entries)

    # in_place：区分白名单与非白名单
    whitelisted = [n for n in entries if n in WHITELIST_IN_PLACE]
    offenders = [n for n in entries if n not in WHITELIST_IN_PLACE]
    if offenders:
        return ConflictResult(status="blocked", offenders=offenders, whitelisted=whitelisted)
    return ConflictResult(status="whitelist_only", whitelisted=whitelisted)
