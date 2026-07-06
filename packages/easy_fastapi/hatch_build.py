# packages/easy_fastapi/hatch_build.py
"""Hatchling 自定义构建钩子：构建时将 .po 编译为 .mo。

为什么需要：框架运行时依赖 .mo 提供 gettext 翻译，但 .mo 是构建产物，
不纳入版本控制（见 .gitignore）。本钩子在 `uv build` / `hatch build` 时
自动编译 src/easy_fastapi/locales/ 下的所有 .po → .mo，并确保它们被打入 wheel。

内联 msgfmt 核心逻辑（仅依赖 re/struct/pathlib），避免触发框架 eager import
导致构建环境缺少 fastapi 等运行时依赖而失败。
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

# ── 内联 msgfmt（与 src/easy_fastapi/ext/i18n/msgfmt.py 逻辑一致） ──

_ESCAPE_RE = re.compile(r'\\(n|t|"|\\)')


def _escape_replace(m: re.Match) -> str:
    ch = m.group(1)
    if ch == "n":
        return "\n"
    if ch == "t":
        return "\t"
    if ch == '"':
        return '"'
    if ch == "\\":
        return "\\"
    return m.group(0)


def _extract_quoted(s: str) -> str:
    s = s.strip()
    if not s.startswith('"') or not s.endswith('"'):
        return s
    s = s[1:-1]
    return _ESCAPE_RE.sub(_escape_replace, s)


def _parse_po(po_path: Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    lines = po_path.read_text(encoding="utf-8").splitlines()
    msgid = msgstr = ""
    in_msgid = in_msgstr = False

    for line in lines:
        line = line.strip()
        if line.startswith("msgid "):
            if in_msgstr and msgid:
                entries.append((msgid, msgstr))
            msgid = _extract_quoted(line[6:])
            msgstr = ""
            in_msgid, in_msgstr = True, False
        elif line.startswith("msgstr "):
            msgstr = _extract_quoted(line[7:])
            in_msgid, in_msgstr = False, True
        elif line.startswith('"') and line.endswith('"'):
            content = _extract_quoted(line)
            if in_msgid:
                msgid += content
            elif in_msgstr:
                msgstr += content
        elif line == "" and in_msgstr:
            if msgid:
                entries.append((msgid, msgstr))
            msgid = msgstr = ""
            in_msgid = in_msgstr = False

    if in_msgstr and msgid:
        entries.append((msgid, msgstr))

    return [(m, s) for m, s in entries if m]


def _make_mo(po_path: Path, mo_path: Path) -> None:
    entries = _parse_po(po_path)
    entries.insert(0, ("", "Content-Type: text/plain; charset=UTF-8\n"))

    keys = [msgid.encode("utf-8") for msgid, _ in entries]
    values = [msgstr.encode("utf-8") for _, msgstr in entries]

    offset = 7 * 4
    orig_table_offset = offset
    offset += len(entries) * 8
    trans_table_offset = offset
    offset += len(entries) * 8
    string_data_start = trans_table_offset + len(entries) * 8

    orig_offsets, pos = [], string_data_start
    for key in keys:
        orig_offsets.append((len(key), pos))
        pos += len(key) + 1
    trans_offsets = []
    for value in values:
        trans_offsets.append((len(value), pos))
        pos += len(value) + 1

    output = bytearray()
    output += struct.pack("<I", 0x950412DE)
    output += struct.pack("<I", 0)
    output += struct.pack("<I", len(entries))
    output += struct.pack("<I", orig_table_offset)
    output += struct.pack("<I", trans_table_offset)
    output += struct.pack("<I", 0)
    output += struct.pack("<I", 0)

    for length, off in orig_offsets:
        output += struct.pack("<II", length, off)
    for length, off in trans_offsets:
        output += struct.pack("<II", length, off)

    for key in keys:
        output += key + b"\x00"
    for value in values:
        output += value + b"\x00"

    mo_path.parent.mkdir(parents=True, exist_ok=True)
    mo_path.write_bytes(bytes(output))


# ── 构建钩子 ──


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        """构建前编译所有 .po → .mo，并强制纳入 wheel 产物。"""
        locales_dir = Path(self.root) / "src" / "easy_fastapi" / "locales"
        if not locales_dir.exists():
            return

        po_files = list(locales_dir.rglob("*.po"))
        for po_path in po_files:
            mo_path = po_path.with_suffix(".mo")
            _make_mo(po_path, mo_path)

        # force_include 确保 .mo 打入 wheel（即使 .gitignore 忽略了它们）
        force_include = build_data.setdefault("force_include", {})
        for po_path in po_files:
            mo_path = po_path.with_suffix(".mo")
            rel = mo_path.relative_to(self.root).as_posix()
            force_include[rel] = rel
