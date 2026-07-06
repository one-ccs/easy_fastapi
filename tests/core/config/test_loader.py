"""ConfigLoader 测试。

覆盖：文件缺失抛错、加载与分段、缺失段返回默认实例、has_section、
path 属性、未知键 forbid 报错、空文件、env 注入影响 section、可注入 environ。
"""

from pathlib import Path

import pytest
from easy_fastapi.core.config.loader import ConfigLoader
from easy_fastapi.core.config.models import EasyFastAPIConfig, FastAPIConfig
from easy_fastapi.core.exceptions import ConfigError


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ---- 文件缺失（错误路径） ----


def test_from_yaml_file_missing_raises(tmp_path):
    with pytest.raises(ConfigError):
        ConfigLoader.from_yaml(tmp_path / "nope.yaml", apply_env=False)


def test_from_yaml_missing_error_message(tmp_path):
    # 报错消息应指出文件名 + 生成项目必须含 easy-fastapi.yaml
    with pytest.raises(ConfigError) as exc_info:
        ConfigLoader.from_yaml(tmp_path / "nope.yaml", apply_env=False)
    msg = str(exc_info.value)
    assert "nope.yaml" in msg
    assert "easy-fastapi.yaml" in msg


def test_from_yaml_is_config_error_subclass(tmp_path):
    # ConfigError 属框架异常体系，可被根异常统一捕获
    from easy_fastapi.core.exceptions import EasyFastAPIError

    with pytest.raises(EasyFastAPIError):
        ConfigLoader.from_yaml(tmp_path / "nope.yaml", apply_env=False)


# ---- 加载与分段（正常路径） ----


def test_from_yaml_loads_and_sections(tmp_path):
    p = _write(tmp_path, "c.yaml", "fastapi:\n  root_path: /api\n")
    loader = ConfigLoader.from_yaml(p, apply_env=False)
    fc = loader.section("fastapi", FastAPIConfig)
    assert fc.root_path == "/api"


def test_section_missing_with_all_defaults_returns_default_instance(tmp_path):
    """section 缺失但模型字段全有默认值 → 返回默认实例（不报错）。"""
    p = _write(tmp_path, "c.yaml", "fastapi:\n  root_path: /api\n")
    loader = ConfigLoader.from_yaml(p, apply_env=False)
    ec = loader.section("easy_fastapi", EasyFastAPIConfig)  # yaml 里没有该段
    assert ec.response_code.style == "http"


def test_has_section(tmp_path):
    p = _write(tmp_path, "c.yaml", "fastapi:\n  root_path: /api\n")
    loader = ConfigLoader.from_yaml(p, apply_env=False)
    assert loader.has_section("fastapi") is True
    assert loader.has_section("redis") is False


def test_path_attribute_stored(tmp_path):
    p = _write(tmp_path, "c.yaml", "fastapi:\n  root_path: /api\n")
    loader = ConfigLoader.from_yaml(p, apply_env=False)
    assert loader.path == p


# ---- 未知键 forbid（错误路径） ----


def test_section_forbid_unknown_key_raises(tmp_path):
    from pydantic import ValidationError

    p = _write(tmp_path, "c.yaml", "fastapi:\n  typo_key: 1\n")
    loader = ConfigLoader.from_yaml(p, apply_env=False)
    with pytest.raises(ValidationError):
        loader.section("fastapi", FastAPIConfig)


# ---- 空文件（边界） ----


def test_from_yaml_empty_file(tmp_path):
    p = _write(tmp_path, "c.yaml", "")
    loader = ConfigLoader.from_yaml(p, apply_env=False)
    # 空文件 → 无任何段
    assert loader.has_section("fastapi") is False
    ec = loader.section("easy_fastapi", EasyFastAPIConfig)
    assert ec.response_code.style == "http"


# ---- env 注入影响 section（集成意图，apply_env=True） ----


def test_from_yaml_applies_env_by_default(tmp_path, monkeypatch):
    p = _write(tmp_path, "c.yaml", "fastapi:\n  root_path: /old\n")
    monkeypatch.setenv("EFA_FASTAPI__ROOT_PATH", "/from-env")
    loader = ConfigLoader.from_yaml(p)  # apply_env 默认 True
    fc = loader.section("fastapi", FastAPIConfig)
    assert fc.root_path == "/from-env"


def test_from_yaml_accepts_injected_environ(tmp_path):
    p = _write(tmp_path, "c.yaml", "fastapi:\n  root_path: /old\n")
    loader = ConfigLoader.from_yaml(p, apply_env=True, environ={"EFA_FASTAPI__ROOT_PATH": "/injected"})
    fc = loader.section("fastapi", FastAPIConfig)
    assert fc.root_path == "/injected"


def test_from_yaml_apply_env_false_ignores_environ(tmp_path):
    p = _write(tmp_path, "c.yaml", "fastapi:\n  root_path: /yaml\n")
    loader = ConfigLoader.from_yaml(p, apply_env=False, environ={"EFA_FASTAPI__ROOT_PATH": "/env"})
    fc = loader.section("fastapi", FastAPIConfig)
    assert fc.root_path == "/yaml"


# ---- 嵌套 section 覆盖（集成意图） ----


def test_section_nested_overrides_defaults(tmp_path):
    p = _write(
        tmp_path,
        "c.yaml",
        "fastapi:\n  swagger:\n    title: From YAML\n  middleware:\n    cors:\n      enabled: true\n",
    )
    loader = ConfigLoader.from_yaml(p, apply_env=False)
    fc = loader.section("fastapi", FastAPIConfig)
    assert fc.swagger.title == "From YAML"
    assert fc.middleware.cors.enabled is True


# ---- env overlay 默认套用契约 ----


def test_from_yaml_env_overlay_priority_over_yaml(tmp_path, monkeypatch):
    """默认 apply_env=True：env 值优先于 yaml 同路径值。"""
    p = _write(tmp_path, "c.yaml", "fastapi:\n  root_path: /api\n")
    monkeypatch.setenv("EFA_FASTAPI__ROOT_PATH", "/v2")
    loader = ConfigLoader.from_yaml(p)
    fc = loader.section("fastapi", FastAPIConfig)
    assert fc.root_path == "/v2"


def test_from_yaml_env_disabled_uses_yaml(tmp_path, monkeypatch):
    """apply_env=False：yaml 值不被 env 覆盖。"""
    p = _write(tmp_path, "c.yaml", "fastapi:\n  root_path: /api\n")
    monkeypatch.setenv("EFA_FASTAPI__ROOT_PATH", "/v2")
    loader = ConfigLoader.from_yaml(p, apply_env=False)
    fc = loader.section("fastapi", FastAPIConfig)
    assert fc.root_path == "/api"


def test_from_yaml_custom_environ_overrides(tmp_path):
    """显式传入 environ dict 时，用该 dict 注入（不读 os.environ）。"""
    p = _write(tmp_path, "c.yaml", "fastapi:\n  root_path: /api\n")
    loader = ConfigLoader.from_yaml(p, environ={"EFA_FASTAPI__ROOT_PATH": "/v3"})
    fc = loader.section("fastapi", FastAPIConfig)
    assert fc.root_path == "/v3"


def test_from_yaml_env_overlay_nested_section(tmp_path, monkeypatch):
    """env 能覆盖 yaml 中缺失的嵌套段（深度集成意图）。"""
    p = _write(tmp_path, "c.yaml", "fastapi:\n  root_path: /api\n")
    monkeypatch.setenv("EFA_FASTAPI__MIDDLEWARE__CORS__ENABLED", "true")
    loader = ConfigLoader.from_yaml(p)
    fc = loader.section("fastapi", FastAPIConfig)
    assert fc.middleware.cors.enabled is True
    assert fc.root_path == "/api"  # yaml 原值保留


def test_from_yaml_empty_environ_dict_no_effect(tmp_path):
    """apply_env=True 但 environ 显式为空 dict → 不注入任何值。"""
    p = _write(tmp_path, "c.yaml", "fastapi:\n  root_path: /api\n")
    loader = ConfigLoader.from_yaml(p, environ={})
    fc = loader.section("fastapi", FastAPIConfig)
    assert fc.root_path == "/api"


def test_from_yaml_env_overlay_coerces_to_typed_field(tmp_path, monkeypatch):
    """env 值经 json.loads 转 bool 后，被 Pydantic bool 字段正确接收（端到端类型链）。"""
    p = _write(tmp_path, "c.yaml", "fastapi:\n  middleware:\n    cors:\n      enabled: false\n")
    monkeypatch.setenv("EFA_FASTAPI__MIDDLEWARE__CORS__ENABLED", "true")
    loader = ConfigLoader.from_yaml(p)
    fc = loader.section("fastapi", FastAPIConfig)
    assert fc.middleware.cors.enabled is True


def test_from_yaml_env_overlay_easy_fastapi_nested_section(tmp_path, monkeypatch):
    """env 能覆盖 easy_fastapi 下的嵌套扩展段（端到端，验证 EFA_EASY_FASTAPI__ 前缀）。"""
    from easy_fastapi.ext.auth.config import AuthConfig

    p = _write(tmp_path, "c.yaml", "easy_fastapi:\n  auth:\n    secret: yaml-secret-min-16ch\n")
    monkeypatch.setenv("EFA_EASY_FASTAPI__AUTH__SECRET", "env-secret-min-16ch")
    loader = ConfigLoader.from_yaml(p)
    ac = loader.section("easy_fastapi.auth", AuthConfig)
    assert ac.secret == "env-secret-min-16ch"


def test_section_dot_path_env_overlay(tmp_path, monkeypatch):
    """loader.section("easy_fastapi.auth") 能读取 env overlay 注入的值。"""
    from easy_fastapi.ext.redis.config import RedisConfig

    p = _write(tmp_path, "c.yaml", "easy_fastapi:\n  redis:\n    enabled: false\n")
    monkeypatch.setenv("EFA_EASY_FASTAPI__REDIS__ENABLED", "true")
    loader = ConfigLoader.from_yaml(p)
    rc = loader.section("easy_fastapi.redis", RedisConfig)
    assert rc.enabled is True
