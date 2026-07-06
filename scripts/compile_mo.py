#!/usr/bin/env python
"""编译框架 .po → .mo（开发期使用）。

用法：
    python scripts/compile_mo.py

本脚本编译 packages/easy_fastapi/src/easy_fastapi/locales/ 下的所有 .po 文件。
开发期 .mo 被 .gitignore 排除，clone 仓库后需运行一次。
正常发布流程由 hatch_build.py 构建钩子自动处理，无需手动运行此脚本。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 确保能导入框架源码
ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "packages" / "easy_fastapi" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from easy_fastapi.ext.i18n.msgfmt import make_mo  # noqa: E402


def main() -> None:
    locales_dir = SRC_DIR / "easy_fastapi" / "locales"
    if not locales_dir.exists():
        print("locales 目录不存在，跳过")
        return

    po_files = list(locales_dir.rglob("*.po"))
    if not po_files:
        print("未找到 .po 文件")
        return

    for po_path in po_files:
        mo_path = po_path.with_suffix(".mo")
        make_mo(po_path, mo_path)
        print(f"编译：{po_path.relative_to(ROOT)} → {mo_path.relative_to(ROOT)}")

    print(f"完成：编译 {len(po_files)} 个文件")


if __name__ == "__main__":
    main()
