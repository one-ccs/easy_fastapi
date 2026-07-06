"""get_config 缓存/单例/清除/None 时通过 marker 自动定位测试。"""

import json

import pytest
from easy_fastapi.core.config.loader import _clear_config_cache, get_config
from easy_fastapi.core.exceptions import ConfigError
from easy_fastapi.project import MARKER_FILENAME


def _write_yaml(path, content="fastapi:\n  swagger:\n    title: test\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_marker(project_dir, *, layout="backend-only"):
    data = {
        "marker_schema_version": 1,
        "project_layout": layout,
        "options": {},
        "registered_extensions": [],
    }
    (project_dir / MARKER_FILENAME).write_text(json.dumps(data), encoding="utf-8")


def test_get_config_caches_by_path(tmp_path):
    _clear_config_cache()
    yaml_path = tmp_path / "easy-fastapi.yaml"
    _write_yaml(yaml_path)
    a = get_config(yaml_path)
    b = get_config(yaml_path)
    assert a is b


def test_get_config_different_paths_different_instances(tmp_path):
    _clear_config_cache()
    p1 = tmp_path / "a" / "easy-fastapi.yaml"
    p2 = tmp_path / "b" / "easy-fastapi.yaml"
    _write_yaml(p1, "fastapi:\n  swagger:\n    title: one\n")
    _write_yaml(p2, "fastapi:\n  swagger:\n    title: two\n")
    assert get_config(p1) is not get_config(p2)


def test_get_config_none_locates_via_marker(tmp_path, monkeypatch):
    _clear_config_cache()
    _write_marker(tmp_path)
    yaml_path = tmp_path / "easy-fastapi.yaml"
    _write_yaml(yaml_path)
    monkeypatch.chdir(tmp_path)
    loader = get_config(None)
    assert loader is not None
    assert get_config(None) is loader


def test_get_config_none_locates_backend_subdir_fullstack(tmp_path, monkeypatch):
    _clear_config_cache()
    _write_marker(tmp_path, layout="fullstack")
    yaml_path = tmp_path / "backend" / "easy-fastapi.yaml"
    _write_yaml(yaml_path)
    monkeypatch.chdir(tmp_path)
    loader = get_config(None)
    assert loader is not None


def test_get_config_none_no_marker_raises(tmp_path, monkeypatch):
    _clear_config_cache()
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError, match=".easy-fastapi.json"):
        get_config(None)


def test_get_config_none_marker_found_but_yaml_missing_raises(tmp_path, monkeypatch):
    _clear_config_cache()
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError, match="easy-fastapi.yaml"):
        get_config(None)


def test_get_config_none_subdir_cwd_raises(tmp_path, monkeypatch):
    """CWD 在项目子目录时报错——必须在项目根目录启动。"""
    _clear_config_cache()
    _write_marker(tmp_path)
    yaml_path = tmp_path / "easy-fastapi.yaml"
    _write_yaml(yaml_path)
    sub_dir = tmp_path / "app" / "routers"
    sub_dir.mkdir(parents=True)
    monkeypatch.chdir(sub_dir)
    with pytest.raises(ConfigError, match=".easy-fastapi.json"):
        get_config(None)


def test_clear_config_cache(tmp_path):
    _clear_config_cache()
    yaml_path = tmp_path / "easy-fastapi.yaml"
    _write_yaml(yaml_path)
    a = get_config(yaml_path)
    _clear_config_cache()
    b = get_config(yaml_path)
    assert a is not b


def test_get_config_nonexistent_file_raises(tmp_path):
    _clear_config_cache()
    with pytest.raises(ConfigError):
        get_config(tmp_path / "nope.yaml")
