# tests/ext/i18n/test_msgfmt.py
"""内嵌 msgfmt（纯 Python .po → .mo 编译器）测试。"""

import gettext
from pathlib import Path

from easy_fastapi.ext.i18n.msgfmt import make_mo, parse_po


def _write_po(path: Path, entries: list[tuple[str, str]], header: str = "") -> None:
    """写一个最小 .po 文件。"""
    lines = []
    if header:
        lines.append(header)
    for msgid, msgstr in entries:
        lines.append(f'msgid "{msgid}"')
        lines.append(f'msgstr "{msgstr}"')
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def test_parse_po_simple(tmp_path):
    """解析 .po 文件提取 msgid/msgstr 对。"""
    po_path = tmp_path / "messages.po"
    _write_po(po_path, [("Hello", "你好"), ("World", "世界")])

    entries = parse_po(po_path)
    assert len(entries) == 2
    assert entries[0] == ("Hello", "你好")
    assert entries[1] == ("World", "世界")


def test_parse_po_skips_header(tmp_path):
    """跳过空 msgid 的 header 条目。"""
    po_path = tmp_path / "messages.po"
    _write_po(
        po_path,
        entries=[("", "header content"), ("Hello", "你好")],
    )

    entries = parse_po(po_path)
    assert len(entries) == 1
    assert entries[0] == ("Hello", "你好")


def test_make_mo_creates_binary_file(tmp_path):
    """make_mo 生成 .mo 二进制文件。"""
    po_path = tmp_path / "messages.po"
    mo_path = tmp_path / "messages.mo"
    _write_po(po_path, [("Hello", "你好"), ("World", "世界")])

    make_mo(po_path, mo_path)

    assert mo_path.exists()
    magic = mo_path.read_bytes()[:4]
    assert magic in (b"\x95\x04\x12\xde", b"\xde\x12\x04\x95")


def test_make_mo_readable_by_gettext(tmp_path):
    """生成的 .mo 文件可被 gettext 正确读取。"""
    po_path = tmp_path / "messages.po"
    mo_path = tmp_path / "messages.mo"

    _write_po(po_path, [("Hello", "你好"), ("World", "世界")])
    make_mo(po_path, mo_path)

    # 将 .mo 放到 gettext 期望的目录结构
    mo_dest = tmp_path / "zh_CN" / "LC_MESSAGES"
    mo_dest.mkdir(parents=True)
    (mo_dest / "messages.mo").write_bytes(mo_path.read_bytes())

    trans = gettext.translation("messages", localedir=str(tmp_path), languages=["zh_CN"])
    assert trans.gettext("Hello") == "你好"
    assert trans.gettext("World") == "世界"


def test_parse_po_multiline_msgid(tmp_path):
    """解析多行 msgid（如带 {name} 占位符的条目）。"""
    po_path = tmp_path / "messages.po"
    content = 'msgid "{name} not found"\nmsgstr "{name}不存在"\n'
    po_path.write_text(content, encoding="utf-8")

    entries = parse_po(po_path)
    assert len(entries) == 1
    assert entries[0] == ("{name} not found", "{name}不存在")


def test_parse_po_escape_sequence_order(tmp_path):
    """转义替换顺序正确：\\\\n（字面反斜杠+n）不应被错误转为换行符。

    回归测试：旧实现用 replace 链，顺序依赖导致 \\\\n 被错误处理。
    新实现用正则一次性替换，无顺序问题。
    """
    from easy_fastapi.ext.i18n.msgfmt import _extract_quoted

    # _extract_quoted 接收 .po 源码中引号内的原始文本
    assert _extract_quoted(r'"Hello\nWorld"') == "Hello\nWorld"  # \n → 换行
    assert _extract_quoted(r'"path\\name"') == "path\\name"  # \\ → 单反斜杠，\n 不触发
    assert _extract_quoted(r'"tab\there"') == "tab\there"  # \t → 制表符
    assert _extract_quoted(r'"quote\"here"') == 'quote"here'  # \" → 双引号
    assert _extract_quoted(r'"back\\slash"') == "back\\slash"  # \\ → 单反斜杠


def test_make_mo_roundtrip_with_escaped_quotes(tmp_path):
    """msgid/msgstr 含双引号时，编译的 .mo 可被 gettext 正确读取。"""
    po_path = tmp_path / "messages.po"
    mo_path = tmp_path / "messages.mo"

    # .po 中双引号用 \\" 转义
    content = 'msgid "He said \\"hello\\""\nmsgstr "他说\\"你好\\""\n'
    po_path.write_text(content, encoding="utf-8")

    make_mo(po_path, mo_path)

    mo_dest = tmp_path / "zh_CN" / "LC_MESSAGES"
    mo_dest.mkdir(parents=True)
    (mo_dest / "messages.mo").write_bytes(mo_path.read_bytes())

    trans = gettext.translation("messages", localedir=str(tmp_path), languages=["zh_CN"])
    assert trans.gettext('He said "hello"') == '他说"你好"'
