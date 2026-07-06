"""read_marker 测试（缺失/损坏报错，≥8 用例）。

read_marker 已下沉到 easy_fastapi.project（CLI 与 Core 共用）。
"""

import pytest
from easy_fastapi.core.exceptions import ConfigError
from easy_fastapi.project import MARKER_FILENAME, read_marker
from easy_fastapi_cli.scaffold.marker import write_marker
from easy_fastapi_cli.scaffold.options import CreateOptions


def _mk(**kw):
    base = {"project_name": "d", "package_name": "d"}
    base.update(kw)
    return CreateOptions(**base)


# ── 1. 往返一致 ──


def test_read_marker_roundtrip(tmp_path):
    o = _mk(database=True, orm="tortoise", db_dialect="mysql")
    write_marker(tmp_path, o, easy_fastapi_version="1.0.0", template_version="1.0.0")
    data = read_marker(tmp_path)
    assert data["options"]["project_name"] == "d"
    assert "orm.tortoise" in data["registered_extensions"]
    assert data["marker_schema_version"] == 1


# ── 2. 缺失 marker 报错 ──


def test_read_marker_missing_raises(tmp_path):
    with pytest.raises(ConfigError):
        read_marker(tmp_path)


# ── 3. 损坏 JSON 报错 ──


def test_read_marker_corrupt_raises(tmp_path):
    (tmp_path / MARKER_FILENAME).write_text("{ not valid json ", encoding="utf-8")
    with pytest.raises(ConfigError):
        read_marker(tmp_path)


# ── 4. 缺失报错消息含 marker 文件名 ──


def test_read_marker_missing_message(tmp_path):
    with pytest.raises(ConfigError) as ei:
        read_marker(tmp_path)
    assert MARKER_FILENAME in str(ei.value)


# ── 5. 损坏报错消息含"损坏"或 json ──


def test_read_marker_corrupt_message(tmp_path):
    (tmp_path / MARKER_FILENAME).write_text("{ broken", encoding="utf-8")
    with pytest.raises(ConfigError) as ei:
        read_marker(tmp_path)
    msg = str(ei.value)
    assert "损坏" in msg or "JSON" in msg or "json" in msg


# ── 6. 读取后字段完整 ──


def test_read_marker_fields_complete(tmp_path):
    o = _mk(frontend=True, database=True, orm="sqlalchemy", db_dialect="sqlite", auth=True, redis=True)
    write_marker(tmp_path, o, easy_fastapi_version="1.0.0", template_version="1.0.0")
    data = read_marker(tmp_path)
    assert data["project_layout"] == "fullstack"
    assert data["easy_fastapi_version"] == "1.0.0"
    assert data["template_version"] == "1.0.0"
    assert "generated_at" in data
    assert "options" in data
    assert "registered_extensions" in data


# ── 7. 空文件报错 ──


def test_read_marker_empty_file_raises(tmp_path):
    (tmp_path / MARKER_FILENAME).write_text("", encoding="utf-8")
    with pytest.raises(ConfigError):
        read_marker(tmp_path)


# ── 8. 合法 JSON 但非对象（如数组）也能读（返回 list）──


def test_read_marker_non_object(tmp_path):
    """合法 JSON（数组）不应报损坏错误，read_marker 仅做 JSON 解析。"""
    (tmp_path / MARKER_FILENAME).write_text("[1,2,3]", encoding="utf-8")
    data = read_marker(tmp_path)
    assert data == [1, 2, 3]


# ── 9. read_marker 返回 dict 类型（正常场景）──


def test_read_marker_returns_dict(tmp_path):
    write_marker(tmp_path, _mk(), easy_fastapi_version="1.0.0", template_version="1.0.0")
    data = read_marker(tmp_path)
    assert isinstance(data, dict)


# ── 10. registered_extensions 往返 ──


def test_read_marker_extensions_roundtrip(tmp_path):
    o = _mk(database=True, orm="sqlmodel", db_dialect="sqlite", auth=True, redis=True)
    write_marker(tmp_path, o, easy_fastapi_version="1.0.0", template_version="1.0.0")
    data = read_marker(tmp_path)
    exts = set(data["registered_extensions"])
    assert {"orm.sqlmodel", "auth", "redis"} <= exts
