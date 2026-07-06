"""core/i18n.py 翻译核心单元测试。"""

import struct
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _reset_locale():
    """每个测试前后重置 i18n 状态。"""
    from easy_fastapi.core.i18n import _current_locale, _current_translator

    _current_locale.set(None)
    _current_translator.set(lambda message: message)
    yield
    _current_locale.set(None)
    _current_translator.set(lambda message: message)


def _write_mo(localedir: Path, entries: dict[str, str]) -> None:
    """手动写最小 .mo 文件（避免依赖 msgfmt 外部工具）。

    entries: {msgid: msgstr} 映射，不含 header entry。
    """
    localedir.mkdir(parents=True, exist_ok=True)

    header_msgstr = "Language: zh_CN\nContent-Type: text/plain; charset=UTF-8\n"
    msgids = [""] + list(entries.keys())
    msgstrs = [header_msgstr] + list(entries.values())
    nstrings = len(msgids)

    header_size = 28  # 7 * 4 bytes
    orig_table_offset = header_size
    trans_table_offset = orig_table_offset + nstrings * 8
    strings_offset = trans_table_offset + nstrings * 8

    # Build string data + table entries
    orig_entries = []
    trans_entries = []
    strings_buf = bytearray()

    for mid, mstr in zip(msgids, msgstrs, strict=False):
        mid_bytes = mid.encode("utf-8") + b"\x00"
        mstr_bytes = mstr.encode("utf-8") + b"\x00"

        orig_entries.append((len(mid_bytes) - 1, strings_offset + len(strings_buf)))
        strings_buf.extend(mid_bytes)

        trans_entries.append((len(mstr_bytes) - 1, strings_offset + len(strings_buf)))
        strings_buf.extend(mstr_bytes)

    # Pack .mo file
    mo = struct.pack(
        "<IIIIIII",
        0x950412DE,  # LE magic
        0,  # revision
        nstrings,
        orig_table_offset,
        trans_table_offset,
        0,  # hash table size
        0,  # hash table offset
    )
    for length, offset in orig_entries:
        mo += struct.pack("<II", length, offset)
    for length, offset in trans_entries:
        mo += struct.pack("<II", length, offset)
    mo += bytes(strings_buf)

    (localedir / "messages.mo").write_bytes(mo)


class TestIdentityFunction:
    """_() 未初始化时为恒等函数。"""

    def test_returns_message_unchanged_without_init(self):
        from easy_fastapi.core.i18n import _

        assert _("Hello") == "Hello"
        assert _("Request failed") == "Request failed"

    def test_returns_empty_string_unchanged(self):
        from easy_fastapi.core.i18n import _

        assert _("") == ""


class TestGetLocale:
    """get_locale() 默认返回 None，set_locale 后返回设置的 locale。"""

    def test_default_locale_is_none(self):
        from easy_fastapi.core.i18n import get_locale

        assert get_locale() is None


class TestSetLocaleAndGettext:
    """set_locale() 加载翻译后，_() 返回翻译结果。"""

    def test_set_locale_with_zh_cn(self, tmp_path):
        """使用 .mo 文件测试 zh_CN 翻译。"""
        _write_mo(
            tmp_path / "zh_CN" / "LC_MESSAGES",
            {
                "Request failed": "请求失败",
                "Request succeeded": "请求成功",
            },
        )

        from easy_fastapi.core.i18n import _, get_locale, set_locale

        set_locale("zh_CN", [tmp_path])
        assert get_locale() == "zh_CN"
        assert _("Request failed") == "请求失败"
        assert _("Request succeeded") == "请求成功"

    def test_set_locale_unknown_msgid_returns_original(self, tmp_path):
        """msgid 无翻译时返回原文。"""
        _write_mo(
            tmp_path / "zh_CN" / "LC_MESSAGES",
            {
                "Request failed": "请求失败",
            },
        )

        from easy_fastapi.core.i18n import _, set_locale

        set_locale("zh_CN", [tmp_path])
        assert _("Unknown message") == "Unknown message"


class TestFallbackChain:
    """add_fallback() 链式查找：项目翻译 → 框架翻译 → msgid。"""

    def test_project_overrides_framework(self, tmp_path):
        """项目翻译优先于框架翻译。"""
        _write_mo(
            tmp_path / "project" / "zh_CN" / "LC_MESSAGES",
            {
                "Request failed": "项目翻译-请求失败",
            },
        )
        _write_mo(
            tmp_path / "framework" / "zh_CN" / "LC_MESSAGES",
            {
                "Request failed": "框架翻译-请求失败",
            },
        )

        from easy_fastapi.core.i18n import _, set_locale

        set_locale("zh_CN", [tmp_path / "project", tmp_path / "framework"])
        assert _("Request failed") == "项目翻译-请求失败"

    def test_framework_fallback_when_project_missing(self, tmp_path):
        """项目翻译没有时 fallback 到框架翻译。"""
        _write_mo(
            tmp_path / "framework" / "zh_CN" / "LC_MESSAGES",
            {
                "Request failed": "框架翻译-请求失败",
            },
        )

        from easy_fastapi.core.i18n import _, set_locale

        # 项目目录没有翻译文件
        set_locale("zh_CN", [tmp_path / "project_not_exist", tmp_path / "framework"])
        assert _("Request failed") == "框架翻译-请求失败"

    def test_neither_translation_returns_msgid(self, tmp_path):
        """两者都没有翻译时返回 msgid。"""
        from easy_fastapi.core.i18n import _, set_locale

        set_locale("zh_CN", [tmp_path / "no_project", tmp_path / "no_framework"])
        assert _("Request failed") == "Request failed"

    def test_project_has_different_msgid_from_framework(self, tmp_path):
        """项目只有部分翻译，其余 fallback 到框架。"""
        _write_mo(
            tmp_path / "project" / "zh_CN" / "LC_MESSAGES",
            {
                "Request failed": "项目-请求失败",
            },
        )
        _write_mo(
            tmp_path / "framework" / "zh_CN" / "LC_MESSAGES",
            {
                "Request failed": "框架-请求失败",
                "Request succeeded": "框架-请求成功",
            },
        )

        from easy_fastapi.core.i18n import _, set_locale

        set_locale("zh_CN", [tmp_path / "project", tmp_path / "framework"])
        # 项目有此翻译 → 用项目的
        assert _("Request failed") == "项目-请求失败"
        # 项目没有 → fallback 到框架
        assert _("Request succeeded") == "框架-请求成功"
        # 都没有 → 返回 msgid
        assert _("Not found") == "Not found"
