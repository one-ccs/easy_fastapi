"""i18n CLI 命令的业务逻辑（不依赖 typer，方便测试）。"""

from __future__ import annotations

import re
from pathlib import Path

from .msgfmt import make_mo, parse_po

# .po 文件中 _() 调用的正则
_MSGID_RE = re.compile(r"""_\(["'](.+?)["']\)""")


def _locales_dir(project_dir: Path) -> Path:
    """返回项目 locales 目录。"""
    return project_dir / "locales"


def do_init(lang: str, *, project_dir: Path) -> None:
    """初始化翻译目录和 .po 文件。

    创建 locales/{lang}/LC_MESSAGES/messages.po 模板。
    目录/文件已存在时跳过不覆盖。
    """
    lc_dir = _locales_dir(project_dir) / lang / "LC_MESSAGES"
    po_path = lc_dir / "messages.po"

    if po_path.exists():
        print(f"已存在：{po_path}")
        return

    lc_dir.mkdir(parents=True, exist_ok=True)

    project_name = project_dir.name
    po_content = f"""\
# {lang} translations for {project_name}.
# Copyright (C) 2026
# This file is distributed under the same license as the {project_name} project.
#
msgid ""
msgstr ""
"Project-Id-Version: {project_name} 0.1.0\\n"
"Report-Msgid-Bugs-To: \\n"
"POT-Creation-Date: 2026-07-06 00:00+0800\\n"
"PO-Revision-Date: 2026-07-06 00:00+0800\\n"
"Last-Translator: \\n"
"Language-Team: {lang}\\n"
"Language: {lang}\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"""
    po_path.write_text(po_content, encoding="utf-8")
    print(f"已创建：{po_path}")


def do_compile(*, project_dir: Path) -> None:
    """编译项目所有 .po → .mo（纯 Python msgfmt）。

    .po 比 .mo 新时才重编译（mtime 比对）。
    """
    locales_dir = _locales_dir(project_dir)

    if not locales_dir.exists():
        raise FileNotFoundError(f"找不到 locales 目录：{locales_dir}，请先运行 efa i18n init")

    po_files = list(locales_dir.rglob("*.po"))
    if not po_files:
        print(f"未找到 .po 文件（{locales_dir}）")
        return

    compiled = 0
    skipped = 0
    for po_path in po_files:
        mo_path = po_path.with_suffix(".mo")
        if mo_path.exists() and mo_path.stat().st_mtime >= po_path.stat().st_mtime:
            skipped += 1
            print(f"跳过（已是最新）：{po_path.relative_to(project_dir)}")
            continue
        make_mo(po_path, mo_path)
        compiled += 1
        print(f"编译：{po_path.relative_to(project_dir)} → {mo_path.relative_to(project_dir)}")

    print(f"完成：编译 {compiled} 个，跳过 {skipped} 个")


def do_update(*, project_dir: Path) -> None:
    """扫描源码 _() 调用，提取 msgid，合并到 .po 文件。

    - 已有翻译 → 保留 msgstr
    - 新增 msgid → 添加条目，msgstr 留空
    - 已删除 msgid → 标记为 obsolete（注释掉，保留翻译）
    """
    locales_dir = _locales_dir(project_dir)

    if not locales_dir.exists():
        raise FileNotFoundError(f"找不到 locales 目录：{locales_dir}，请先运行 efa i18n init")

    # 1. 扫描源码提取 msgid
    source_msgids = _extract_msgids(project_dir)
    print(f"扫描到 {len(source_msgids)} 个 msgid")

    # 2. 合并到每个 locale 的 .po 文件
    po_files = list(locales_dir.rglob("*.po"))
    if not po_files:
        print(f"未找到 .po 文件（{locales_dir}）")
        return

    for po_path in po_files:
        _merge_po(po_path, source_msgids, project_dir)
        print(f"更新：{po_path.relative_to(project_dir)}")


def _extract_msgids(project_dir: Path) -> set[str]:
    """扫描项目 app/ 目录下所有 .py 文件的 _() 调用，提取 msgid。"""
    msgids: set[str] = set()
    app_dir = project_dir / "app"
    if not app_dir.exists():
        return msgids

    for py_file in app_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue
        for match in _MSGID_RE.finditer(content):
            msgids.add(match.group(1))

    return msgids


def _po_escape(s: str) -> str:
    """转义 .po 文件中的特殊字符（双引号、换行、制表符、反斜杠）。"""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")


def _merge_po(po_path: Path, source_msgids: set[str], project_dir: Path) -> None:
    """合并 msgid 到 .po 文件。"""
    # 解析现有条目
    existing = parse_po(po_path)
    existing_dict = {msgid: msgstr for msgid, msgstr in existing}

    # 分类
    new_msgids = source_msgids - set(existing_dict.keys())
    obsolete_msgids = set(existing_dict.keys()) - source_msgids

    # 重写 .po 文件
    header = _read_po_header(po_path)
    lines = [header, ""] if header else []

    # 保留的条目（按原有顺序）
    for msgid, msgstr in existing:
        if msgid in source_msgids:
            lines.append(f'msgid "{_po_escape(msgid)}"')
            lines.append(f'msgstr "{_po_escape(msgstr)}"')
            lines.append("")

    # 新增条目
    for msgid in sorted(new_msgids):
        lines.append(f'msgid "{_po_escape(msgid)}"')
        lines.append('msgstr ""')
        lines.append("")

    # obsolete 条目（注释掉保留翻译）
    for msgid in sorted(obsolete_msgids):
        msgstr = existing_dict.get(msgid, "")
        lines.append(f'#~ msgid "{_po_escape(msgid)}"')
        lines.append(f'#~ msgstr "{_po_escape(msgstr)}"')
        lines.append("")

    po_path.write_text("\n".join(lines), encoding="utf-8")


def _read_po_header(po_path: Path) -> str:
    """读取 .po 文件的 header 部分（msgid "" ... msgstr "..." 块）。"""
    content = po_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    header_lines: list[str] = []
    in_header = False
    header_started = False

    for line in lines:
        stripped = line.strip()
        if not header_started:
            if stripped.startswith('msgid ""') or stripped.startswith('msgid "'):
                # 可能是 header（msgid 为空或以空开头的多行）
                if stripped == 'msgid ""':
                    header_started = True
                    in_header = True
                    header_lines.append(line)
                else:
                    # 非 header 的 msgid 行，停止
                    break
            elif stripped.startswith("#"):
                # 注释属于 header
                header_lines.append(line)
            elif stripped == "":
                header_lines.append(line)
            else:
                break
        else:
            # header 已开始
            if stripped.startswith("msgstr") or stripped.startswith('"'):
                header_lines.append(line)
            elif stripped == "" and not in_header:
                break
            elif stripped == "":
                header_lines.append(line)
                in_header = False
            else:
                break

    return "\n".join(header_lines)
