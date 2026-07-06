"""I18n 运行时扩展（中间件 + set_locale + fallback 链）。

职责：
1. init_app 时注册 ASGI 中间件，每个请求根据 Accept-Language 设置 locale
2. 加载框架翻译 + 项目翻译，串联 add_fallback() 链
3. ctx.provide("i18n", ...) 供其他扩展查询当前 locale
"""

from __future__ import annotations

import gettext
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from .config import I18nConfig

if TYPE_CHECKING:
    from fastapi import FastAPI

    from easy_fastapi.core.extension import ExtensionContext


# ── 翻译缓存：避免每请求重复读取 .mo 文件 ──
# key = (locale, tuple(localedirs_str), domain)
_translation_cache: dict[tuple, gettext.NullTranslations] = {}


def _load_translations(
    locale: str,
    localedirs: Sequence[str | Path],
    domain: str = "messages",
) -> gettext.NullTranslations:
    """加载并缓存 gettext 翻译对象，串联 fallback 链。

    首次调用后缓存结果，后续同参数请求直接返回缓存对象。

    .mo 不存在但 .po 存在时按需编译（仅 editable install 场景触发；
    wheel 安装时 .mo 已随包发布，不会走到这里）。
    """
    from easy_fastapi.core.i18n import _ensure_mo_compiled

    cache_key = (locale, tuple(str(d) for d in localedirs), domain)
    if cache_key in _translation_cache:
        return _translation_cache[cache_key]

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

    _translation_cache[cache_key] = translations
    return translations


def _parse_accept_language(header: str) -> list[tuple[str, float]]:
    """解析 Accept-Language header，返回按 q 值降序排列的 (tag, q) 列表。

    符合 RFC 7231：缺省 q=1.0，无效 q 值视为 0。
    """
    result: list[tuple[str, float]] = []
    for part in header.split(","):
        part = part.strip()
        if not part:
            continue
        if ";" in part:
            tag, *params = part.split(";")
            tag = tag.strip()
            q = 1.0
            for param in params:
                param = param.strip()
                if param.startswith("q="):
                    try:
                        q = float(param[2:])
                    except ValueError:
                        q = 0.0
            result.append((tag, q))
        else:
            result.append((part, 1.0))
    result.sort(key=lambda x: x[1], reverse=True)
    return result


def _match_locale(accept_language: str, available: list[str]) -> str | None:
    """从 Accept-Language header 匹配可用的 locale。

    按 RFC 7231 q 值降序匹配：zh-CN;q=1.0, en;q=0.9 → 优先匹配 zh-CN。
    将 header 值中的 `-` 替换为 `_`，支持前缀匹配（zh → zh_CN）。
    """
    for tag, _q in _parse_accept_language(accept_language):
        # 标准化：zh-CN → zh_CN
        normalized = tag.replace("-", "_")

        # 精确匹配
        if normalized in available:
            return normalized

        # 前缀匹配：zh → zh_CN, en → en_US
        prefix = normalized.split("_")[0]
        for loc in available:
            if loc.split("_")[0] == prefix:
                return loc

    return None


class I18nExtension:
    name = "i18n"
    requires: ClassVar[list[str]] = []

    def config_model(self):
        return I18nConfig

    def init_app(self, app: FastAPI, config: I18nConfig | None, ctx: ExtensionContext) -> None:
        cfg = config or I18nConfig()

        # 框架内置翻译目录
        import easy_fastapi

        framework_localedir = Path(easy_fastapi.__file__).parent / "locales"

        # 项目翻译目录：复用 project.py 统一推导规则
        # fullstack: project_root/backend/locales
        # backend-only: project_root/locales
        loader = ctx.get_loader()
        if loader and loader.path:
            from easy_fastapi.project import resolve_app_dir_from_config

            project_localedir = resolve_app_dir_from_config(loader.path) / "locales"
        else:
            # fallback: 用 cwd（非正常启动路径，如测试环境无 loader）
            project_localedir = Path.cwd() / "locales"
        localedirs = [project_localedir, framework_localedir]

        # 用 default_locale 预初始化翻译函数，使启动阶段 _() 也能翻译
        # （路由 summary 等装饰器参数在 import 时求值，此时无请求上下文）
        from easy_fastapi.core.i18n import _current_locale, _current_translator

        translations = _load_translations(cfg.default_locale, localedirs)
        _current_locale.set(cfg.default_locale)
        _current_translator.set(translations.gettext)

        @app.middleware("http")
        async def i18n_middleware(request, call_next):
            from easy_fastapi.core.i18n import _current_locale, _current_translator

            accept_lang = request.headers.get("Accept-Language", "")
            locale = _match_locale(accept_lang, cfg.available_locales) if accept_lang else None
            if locale is None:
                locale = cfg.default_locale

            # 使用缓存的翻译对象，只切换 ContextVar
            translations = _load_translations(locale, localedirs)
            _current_locale.set(locale)
            _current_translator.set(translations.gettext)

            try:
                response = await call_next(request)
            finally:
                # 防御性重置：ASGI 请求有独立 context，此步非必须但增强可读性
                _current_locale.set(None)
                _current_translator.set(lambda message: message)

            return response

        ctx.provide("i18n", self)
