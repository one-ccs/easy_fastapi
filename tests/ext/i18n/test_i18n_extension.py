"""I18nExtension 扩展测试。"""

import pathlib

import pytest
from easy_fastapi import EasyFastAPI
from easy_fastapi.core.i18n import _current_locale, _current_translator
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_i18n():
    """每个测试前后重置 i18n 状态。"""
    _current_locale.set(None)
    _current_translator.set(lambda message: message)
    yield
    _current_locale.set(None)
    _current_translator.set(lambda message: message)


@pytest.fixture(autouse=True)
def _clear_translation_cache():
    """每个测试后清除翻译缓存，避免跨测试污染。"""
    yield
    from easy_fastapi.ext.i18n.extension import _translation_cache

    _translation_cache.clear()


def _yaml_config(tmp_path, i18n_section: str = "") -> pathlib.Path:
    """生成 YAML 配置文件。"""
    content = "fastapi:\n  root_path: ''\n"
    if i18n_section:
        content += f"\neasy_fastapi:\n  i18n:\n{i18n_section}\n"
    p = tmp_path / "easy-fastapi.yaml"
    p.write_text(content, encoding="utf-8")
    return p


class TestI18nConfig:
    def test_default_config(self):
        from easy_fastapi.ext.i18n.config import I18nConfig

        cfg = I18nConfig()
        assert cfg.default_locale == "zh_CN"
        assert cfg.available_locales == ["zh_CN", "en_US"]

    def test_extra_forbidden(self):
        from easy_fastapi.ext.i18n.config import I18nConfig

        with pytest.raises(ValueError):
            I18nConfig(default_locale="zh_CN", unknown_field=True)

    def test_custom_locales(self):
        from easy_fastapi.ext.i18n.config import I18nConfig

        cfg = I18nConfig(default_locale="en_US", available_locales=["en_US", "ja_JP"])
        assert cfg.default_locale == "en_US"
        assert cfg.available_locales == ["en_US", "ja_JP"]

    def test_default_locale_must_be_in_available(self):
        from easy_fastapi.ext.i18n.config import I18nConfig

        with pytest.raises(Exception, match="default_locale"):
            I18nConfig(default_locale="fr_FR", available_locales=["zh_CN", "en_US"])


class TestI18nExtensionRegistration:
    def test_get_extension_returns_i18n(self):
        from easy_fastapi.ext import get_extension

        ext = get_extension("i18n")
        from easy_fastapi.ext.i18n.extension import I18nExtension

        assert isinstance(ext, I18nExtension)

    def test_extension_name(self):
        from easy_fastapi.ext.i18n.extension import I18nExtension

        ext = I18nExtension()
        assert ext.name == "i18n"


class TestStartupTranslation:
    """守护测试：I18nExtension.init_app 用 default_locale 预初始化 _current_translator。

    路由 summary 等装饰器参数在模块 import 时求值，此时无请求上下文，
    中间件尚未运行。若不预初始化，_() 会 fallback 到英文原文。
    """

    def _make_app(self, tmp_path, i18n_yaml: str = ""):
        app = FastAPI()
        easy = EasyFastAPI(app, config_path=_yaml_config(tmp_path, i18n_yaml))

        from easy_fastapi.ext.i18n.extension import I18nExtension

        easy.use(I18nExtension())
        return app

    def test_translator_preinitialized_to_default_locale(self, tmp_path):
        """use(I18nExtension) 后，无请求上下文时 _() 也应返回 default_locale 翻译。"""
        self._make_app(tmp_path)

        from easy_fastapi.core.i18n import _

        # 框架 .mo 包含 "Request succeeded" → "请求成功"
        assert _("Request succeeded") == "请求成功"

    def test_preinitialization_respects_custom_default_locale(self, tmp_path):
        """配置 default_locale=en_US 时，启动阶段 _() 应返回英文。"""
        yaml = "    default_locale: en_US\n    available_locales:\n      - en_US\n      - zh_CN\n"
        self._make_app(tmp_path, yaml)

        from easy_fastapi.core.i18n import _

        assert _("Request succeeded") == "Request succeeded"


class TestI18nMiddleware:
    def _make_app(self, tmp_path, i18n_yaml: str = ""):
        """创建装配了 I18nExtension 的测试应用。"""
        app = FastAPI()
        easy = EasyFastAPI(app, config_path=_yaml_config(tmp_path, i18n_yaml))

        from easy_fastapi.ext.i18n.extension import I18nExtension

        easy.use(I18nExtension())
        return app

    def test_default_locale_when_no_header(self, tmp_path):
        """无 Accept-Language header 时使用默认 locale。"""
        app = self._make_app(tmp_path)

        @app.get("/test")
        async def test_route():
            from easy_fastapi.core.i18n import get_locale

            return {"locale": get_locale()}

        with TestClient(app) as client:
            resp = client.get("/test")
        assert resp.json()["locale"] == "zh_CN"

    def test_zh_cn_locale_from_header(self, tmp_path):
        """Accept-Language: zh-CN 使用 zh_CN locale。"""
        app = self._make_app(tmp_path)

        @app.get("/test")
        async def test_route():
            from easy_fastapi.core.i18n import get_locale

            return {"locale": get_locale()}

        with TestClient(app) as client:
            resp = client.get("/test", headers={"Accept-Language": "zh-CN"})
        assert resp.json()["locale"] == "zh_CN"

    def test_en_us_locale_from_header(self, tmp_path):
        """Accept-Language: en 使用 en_US locale。"""
        app = self._make_app(tmp_path)

        @app.get("/test")
        async def test_route():
            from easy_fastapi.core.i18n import get_locale

            return {"locale": get_locale()}

        with TestClient(app) as client:
            resp = client.get("/test", headers={"Accept-Language": "en"})
        assert resp.json()["locale"] == "en_US"

    def test_fallback_to_default_for_unknown_locale(self, tmp_path):
        """未知 locale fallback 到默认 locale。"""
        app = self._make_app(tmp_path)

        @app.get("/test")
        async def test_route():
            from easy_fastapi.core.i18n import get_locale

            return {"locale": get_locale()}

        with TestClient(app) as client:
            resp = client.get("/test", headers={"Accept-Language": "fr"})
        assert resp.json()["locale"] == "zh_CN"  # fallback to default

    def test_translation_works_in_request(self, tmp_path):
        """请求内 _() 返回翻译后的消息。"""
        app = self._make_app(tmp_path)

        @app.get("/test")
        async def test_route():
            from easy_fastapi.core.i18n import _

            return {"message": _("Request succeeded")}

        with TestClient(app) as client:
            # zh_CN → 应返回中文
            resp = client.get("/test", headers={"Accept-Language": "zh-CN"})
        data = resp.json()
        assert data["message"] == "请求成功"

    def test_custom_default_locale(self, tmp_path):
        """自定义默认 locale。"""
        i18n_yaml = "    default_locale: en_US\n    available_locales:\n      - en_US\n      - zh_CN\n"
        app = self._make_app(tmp_path, i18n_yaml)

        @app.get("/test")
        async def test_route():
            from easy_fastapi.core.i18n import get_locale

            return {"locale": get_locale()}

        with TestClient(app) as client:
            resp = client.get("/test")
        assert resp.json()["locale"] == "en_US"


class TestMatchLocale:
    def test_exact_match(self):
        from easy_fastapi.ext.i18n.extension import _match_locale

        assert _match_locale("zh_CN", ["zh_CN", "en_US"]) == "zh_CN"

    def test_prefix_match(self):
        from easy_fastapi.ext.i18n.extension import _match_locale

        assert _match_locale("zh", ["zh_CN", "en_US"]) == "zh_CN"

    def test_hyphen_to_underscore(self):
        from easy_fastapi.ext.i18n.extension import _match_locale

        assert _match_locale("zh-CN", ["zh_CN", "en_US"]) == "zh_CN"

    def test_en_prefix(self):
        from easy_fastapi.ext.i18n.extension import _match_locale

        assert _match_locale("en", ["zh_CN", "en_US"]) == "en_US"

    def test_unknown_returns_none(self):
        from easy_fastapi.ext.i18n.extension import _match_locale

        assert _match_locale("fr", ["zh_CN", "en_US"]) is None

    def test_complex_header_respects_q_values(self):
        """Accept-Language 含 q 权重时按优先级匹配。"""
        from easy_fastapi.ext.i18n.extension import _match_locale

        # en;q=1.0, zh-CN;q=0.9 → 优先匹配 en
        assert _match_locale("en;q=1.0,zh-CN;q=0.9", ["zh_CN", "en_US"]) == "en_US"

    def test_complex_header_default_q_is_1(self):
        """无 q 值的标签 q=1.0（最高优先级）。"""
        from easy_fastapi.ext.i18n.extension import _match_locale

        assert _match_locale("zh-CN,zh;q=0.9,en;q=0.8", ["zh_CN", "en_US"]) == "zh_CN"

    def test_q_weight_selects_higher(self):
        """q 值高的标签优先匹配。"""
        from easy_fastapi.ext.i18n.extension import _match_locale

        assert _match_locale("en;q=0.5,zh-CN;q=0.9", ["zh_CN", "en_US"]) == "zh_CN"


class TestParseAcceptLanguage:
    def test_single_tag_no_q(self):
        from easy_fastapi.ext.i18n.extension import _parse_accept_language

        result = _parse_accept_language("zh-CN")
        assert result == [("zh-CN", 1.0)]

    def test_multiple_tags_with_q(self):
        from easy_fastapi.ext.i18n.extension import _parse_accept_language

        result = _parse_accept_language("en;q=0.9,zh-CN;q=1.0")
        assert result[0] == ("zh-CN", 1.0)
        assert result[1] == ("en", 0.9)

    def test_default_q_is_1(self):
        from easy_fastapi.ext.i18n.extension import _parse_accept_language

        result = _parse_accept_language("zh-CN,en;q=0.8")
        assert result[0] == ("zh-CN", 1.0)
        assert result[1] == ("en", 0.8)

    def test_invalid_q_treated_as_zero(self):
        from easy_fastapi.ext.i18n.extension import _parse_accept_language

        result = _parse_accept_language("fr;q=invalid,en;q=0.5")
        assert result[0] == ("en", 0.5)
        assert result[1] == ("fr", 0.0)


class TestTranslationCache:
    def test_cache_returns_same_object(self, tmp_path):
        """相同参数的两次调用返回同一翻译对象。"""
        from pathlib import Path

        import easy_fastapi
        from easy_fastapi.ext.i18n.extension import _load_translations, _translation_cache

        framework_localedir = Path(easy_fastapi.__file__).parent / "locales"
        _translation_cache.clear()

        t1 = _load_translations("zh_CN", [framework_localedir])
        t2 = _load_translations("zh_CN", [framework_localedir])
        assert t1 is t2

    def test_different_locale_returns_different_object(self, tmp_path):
        """不同 locale 返回不同翻译对象。"""
        from pathlib import Path

        import easy_fastapi
        from easy_fastapi.ext.i18n.extension import _load_translations, _translation_cache

        framework_localedir = Path(easy_fastapi.__file__).parent / "locales"
        _translation_cache.clear()

        t1 = _load_translations("zh_CN", [framework_localedir])
        t2 = _load_translations("en_US", [framework_localedir])
        assert t1 is not t2


class TestOnDemandCompile:
    """守护测试：.mo 不存在但 .po 存在时按需编译。"""

    def test_ensure_mo_compiled_creates_mo_from_po(self, tmp_path):
        """_ensure_mo_compiled 在 .mo 不存在时从 .po 编译。"""
        from easy_fastapi.core.i18n import _ensure_mo_compiled

        lc_dir = tmp_path / "zh_CN" / "LC_MESSAGES"
        lc_dir.mkdir(parents=True)

        # 写一个简单的 .po 文件
        po_path = lc_dir / "messages.po"
        po_path.write_text(
            'msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\nmsgid "Hello"\nmsgstr "你好"\n',
            encoding="utf-8",
        )

        mo_path = lc_dir / "messages.mo"
        assert not mo_path.exists()

        _ensure_mo_compiled(tmp_path, "zh_CN", "messages")

        assert mo_path.exists()
        # 编译后的 .mo 应能被 gettext 正确读取
        import gettext

        trans = gettext.translation("messages", localedir=str(tmp_path), languages=["zh_CN"])
        assert trans.gettext("Hello") == "你好"

    def test_ensure_mo_compiled_skips_when_mo_exists(self, tmp_path):
        """_ensure_mo_compiled 在 .mo 已存在时跳过编译。"""
        from easy_fastapi.core.i18n import _ensure_mo_compiled

        lc_dir = tmp_path / "zh_CN" / "LC_MESSAGES"
        lc_dir.mkdir(parents=True)
        po_path = lc_dir / "messages.po"
        po_path.write_text('msgid "A"\nmsgstr "B"\n', encoding="utf-8")
        mo_path = lc_dir / "messages.mo"
        mo_path.write_bytes(b"fake-mo-content")

        _ensure_mo_compiled(tmp_path, "zh_CN", "messages")

        # 不应覆盖已存在的 .mo
        assert mo_path.read_bytes() == b"fake-mo-content"

    def test_ensure_mo_compiled_skips_when_po_missing(self, tmp_path):
        """_ensure_mo_compiled 在 .po 不存在时跳过。"""
        from easy_fastapi.core.i18n import _ensure_mo_compiled

        lc_dir = tmp_path / "zh_CN" / "LC_MESSAGES"
        lc_dir.mkdir(parents=True)
        # 不写 .po

        _ensure_mo_compiled(tmp_path, "zh_CN", "messages")

        # 不应创建任何 .mo
        assert not (lc_dir / "messages.mo").exists()
