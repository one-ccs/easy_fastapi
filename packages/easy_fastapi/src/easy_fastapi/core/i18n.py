"""翻译核心：contextvars + gettext 封装。

提供 set_locale()、get_locale()、_() 三个函数。
未调用 set_locale() 时 _() 为恒等函数（返回 msgid 英文原文）。
set_locale() 接收 localedirs 序列，按 add_fallback() 链式查找：
项目翻译 → 框架翻译 → msgid。
"""

from __future__ import annotations

import gettext
from collections.abc import Sequence
from contextvars import ContextVar
from pathlib import Path

# 当前 locale（默认 None，表示未初始化）
_current_locale: ContextVar[str | None] = ContextVar("current_locale", default=None)

# 当前翻译函数（默认恒等函数）
_current_translator: ContextVar = ContextVar(
    "current_translator",
    default=lambda message: message,
)


def set_locale(
    locale: str,
    localedirs: Sequence[str | Path],
    domain: str = "messages",
) -> None:
    """设置当前请求的 locale，加载 gettext 翻译对象并串联 fallback 链。

    localedirs 按顺序串联 add_fallback()：第一个为主翻译（项目），
    后续为 fallback（框架等）。查找顺序：主翻译 → fallback → msgid。

    gettext.translation(..., fallback=True) 在找不到 .mo 时返回 NullTranslations，
    因此 translations 始终非 None，无需额外空值检查。

    .mo 不存在但 .po 存在时按需编译（editable install 兜底；wheel 安装时
    .mo 已随包发布，此步为 no-op）。
    """
    for localedir in localedirs:
        _ensure_mo_compiled(localedir, locale, domain)

    translations: gettext.NullTranslations | None = None
    for localedir in localedirs:
        trans = gettext.translation(
            domain,
            localedir=str(localedir),
            languages=[locale],
            fallback=True,
        )
        if translations is None:
            translations = trans
        else:
            translations.add_fallback(trans)

    _current_locale.set(locale)
    # fallback=True 保证 translations 至少是 NullTranslations
    _current_translator.set(translations.gettext)


def _ensure_mo_compiled(localedir: str | Path, locale: str, domain: str) -> None:
    """若 .mo 不存在但 .po 存在，则现场编译（开发期 editable install 兜底）。

    wheel 发布的框架已含 .mo，此函数是 no-op；仅当开发者通过 uv.sources
    指向本地源码、且 .mo 被 gitignore 排除时才会真正编译。
    """
    po_path = Path(localedir) / locale / "LC_MESSAGES" / f"{domain}.po"
    mo_path = po_path.with_suffix(".mo")
    if not po_path.exists() or mo_path.exists():
        return
    # 延迟导入避免 core 层硬依赖 ext.msgfmt
    from easy_fastapi.ext.i18n.msgfmt import make_mo

    make_mo(po_path, mo_path)


def get_locale() -> str | None:
    """获取当前 locale。"""
    return _current_locale.get()


def _(message: str) -> str:
    """翻译函数：查当前 locale 的翻译链，未初始化时返回原文。"""
    return _current_translator.get()(message)
