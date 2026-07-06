# packages/easy_fastapi/src/easy_fastapi/ext/i18n/msgfmt.py
"""纯 Python msgfmt：将 .po 文件编译为 .mo 二进制文件。

基于 CPython Tools/i18n/msgfmt.py 精简而来，无外部依赖。
解决 Windows 无系统 msgfmt 命令的问题。
"""

from __future__ import annotations

import re
import struct
from pathlib import Path


def parse_po(po_path: Path) -> list[tuple[str, str]]:
    """解析 .po 文件，返回 (msgid, msgstr) 列表。跳过空 msgid 的 header 条目。"""
    entries: list[tuple[str, str]] = []
    lines = po_path.read_text(encoding="utf-8").splitlines()

    msgid = ""
    msgstr = ""
    in_msgid = False
    in_msgstr = False

    for line in lines:
        line = line.strip()
        if line.startswith("msgid "):
            # 保存上一个条目
            if in_msgstr and msgid:
                entries.append((msgid, msgstr))
            msgid = _extract_quoted(line[6:])
            msgstr = ""
            in_msgid = True
            in_msgstr = False
        elif line.startswith("msgstr "):
            msgstr = _extract_quoted(line[7:])
            in_msgid = False
            in_msgstr = True
        elif line.startswith('"') and line.endswith('"'):
            # 续行
            content = _extract_quoted(line)
            if in_msgid:
                msgid += content
            elif in_msgstr:
                msgstr += content
        elif line == "" and in_msgstr:
            # 空行结束当前条目
            if msgid:
                entries.append((msgid, msgstr))
            msgid = ""
            msgstr = ""
            in_msgid = False
            in_msgstr = False
        # 注释行（# 开头）和空行（非条目间）跳过

    # 文件末尾可能没有空行
    if in_msgstr and msgid:
        entries.append((msgid, msgstr))

    # 跳过空 msgid（header）
    return [(m, s) for m, s in entries if m]


def make_mo(po_path: Path, mo_path: Path) -> None:
    """将 .po 文件编译为 .mo 二进制文件。

    自动注入空 msgid 的 header 条目（含 Content-Type charset=UTF-8），
    以便 gettext 正确解码非 ASCII 翻译文本。
    """
    entries = parse_po(po_path)
    # 确保 header 条目（空 msgid）存在，gettext 依赖它确定 charset
    header = "Content-Type: text/plain; charset=UTF-8\n"
    entries.insert(0, ("", header))
    _write_mo(entries, mo_path)


def _extract_quoted(s: str) -> str:
    """提取引号内的内容，处理转义。

    使用正则一次性替换所有转义序列，避免 replace 链的顺序依赖问题
    （如 \\n 先被 \\\\→\\ 还原为 \n，再被 \\n→\\n 错误转为换行符）。
    """
    s = s.strip()
    if not s.startswith('"') or not s.endswith('"'):
        return s
    s = s[1:-1]
    s = _ESCAPE_RE.sub(_escape_replace, s)
    return s


# 转义序列正则：匹配 \\n, \\t, \\", \\\\
_ESCAPE_RE = re.compile(r'\\(n|t|"|\\)')


def _escape_replace(m: re.Match) -> str:
    """转义序列替换回调。"""
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


def _write_mo(entries: list[tuple[str, str]], mo_path: Path) -> None:
    """写入 .mo 二进制文件（GNU gettext 格式）。"""
    keys = [msgid.encode("utf-8") for msgid, _ in entries]
    values = [msgstr.encode("utf-8") for _, msgstr in entries]

    # 偏移量计算
    offset = 7 * 4  # header 大小
    orig_table_offset = offset
    offset += len(entries) * 8
    trans_table_offset = offset
    offset += len(entries) * 8
    # strings 数据区起始
    string_data_start = trans_table_offset + len(entries) * 8

    orig_offsets = []
    pos = string_data_start
    for key in keys:
        orig_offsets.append((len(key), pos))
        pos += len(key) + 1

    trans_offsets = []
    for value in values:
        trans_offsets.append((len(value), pos))
        pos += len(value) + 1

    # 写入
    output = bytearray()
    output += struct.pack("<I", 0x950412DE)  # magic
    output += struct.pack("<I", 0)  # revision
    output += struct.pack("<I", len(entries))  # nstrings
    output += struct.pack("<I", orig_table_offset)
    output += struct.pack("<I", trans_table_offset)
    output += struct.pack("<I", 0)  # hash_table_size
    output += struct.pack("<I", 0)  # hash_table_offset

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
