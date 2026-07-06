"""write_marker 测试（代码写入+派生字段+扩展推导，≥8 用例）。"""

import json

from easy_fastapi_cli.scaffold.marker import MARKER_FILENAME, write_marker
from easy_fastapi_cli.scaffold.options import CreateOptions


def _mk(**kw):
    base = {"project_name": "demo", "package_name": "demo"}
    base.update(kw)
    return CreateOptions(**base)


# ── 1. 创建 .easy-fastapi.json ──


def test_write_marker_creates_file(tmp_path):
    o = _mk(database=True, orm="tortoise", db_dialect="mysql", auth=True, redis=True, frontend=True)
    write_marker(tmp_path, o, easy_fastapi_version="1.0.0", template_version="1.0.0")
    marker_path = tmp_path / MARKER_FILENAME
    assert marker_path.exists()
    data = json.loads(marker_path.read_text(encoding="utf-8"))
    assert data["marker_schema_version"] == 1
    assert data["easy_fastapi_version"] == "1.0.0"
    assert data["template_version"] == "1.0.0"


# ── 2. generated_at 非空 ──


def test_marker_generated_at_present(tmp_path):
    write_marker(tmp_path, _mk(), easy_fastapi_version="1.0.0", template_version="1.0.0")
    data = json.loads((tmp_path / MARKER_FILENAME).read_text(encoding="utf-8"))
    assert "generated_at" in data
    assert "T" in data["generated_at"]


# ── 3. project_layout 正确 ──


def test_marker_project_layout(tmp_path):
    o = _mk(frontend=True)
    write_marker(tmp_path, o, easy_fastapi_version="1.0.0", template_version="1.0.0")
    data = json.loads((tmp_path / MARKER_FILENAME).read_text(encoding="utf-8"))
    assert data["project_layout"] == "fullstack"


def test_marker_project_layout_backend_only(tmp_path):
    o = _mk()
    write_marker(tmp_path, o, easy_fastapi_version="1.0.0", template_version="1.0.0")
    data = json.loads((tmp_path / MARKER_FILENAME).read_text(encoding="utf-8"))
    assert data["project_layout"] == "backend-only"


# ── 4. registered_extensions 推导正确 ──


def test_marker_registered_extensions_derived(tmp_path):
    o = _mk(
        database=True,
        orm="tortoise",
        db_dialect="mysql",
        auth=True,
        redis=True,
        migration=True,
        frontend=True,
        static=True,
    )
    write_marker(tmp_path, o, easy_fastapi_version="1.0.0", template_version="1.0.0")
    data = json.loads((tmp_path / MARKER_FILENAME).read_text(encoding="utf-8"))
    exts = set(data["registered_extensions"])
    assert "orm.tortoise" in exts
    assert "auth" in exts
    assert "redis" in exts
    assert "migration" not in exts
    assert "frontend" not in exts
    assert "static" not in exts


# ── 5. options 快照含 project_name ──


def test_marker_options_snapshot(tmp_path):
    o = _mk()
    write_marker(tmp_path, o, easy_fastapi_version="1.0.0", template_version="1.0.0")
    data = json.loads((tmp_path / MARKER_FILENAME).read_text(encoding="utf-8"))
    assert data["options"]["project_name"] == "demo"


# ── 6. frontend_ui 字段已移除 ──


def test_marker_no_frontend_ui_field(tmp_path):
    o = _mk(frontend=True)
    write_marker(tmp_path, o, easy_fastapi_version="1.0.0", template_version="1.0.0")
    data = json.loads((tmp_path / MARKER_FILENAME).read_text(encoding="utf-8"))
    assert "frontend_ui" not in data["options"]


# ── 8. registered_extensions 空（无 ORM/auth/redis）──


def test_marker_no_extensions_when_minimal(tmp_path):
    o = _mk()
    write_marker(tmp_path, o, easy_fastapi_version="1.0.0", template_version="1.0.0")
    data = json.loads((tmp_path / MARKER_FILENAME).read_text(encoding="utf-8"))
    assert data["registered_extensions"] == []


# ── 9. MARKER_FILENAME 常量 ──


def test_marker_filename():
    assert MARKER_FILENAME == ".easy-fastapi.json"


# ── 10. SQLModel ORM 扩展名 ──


def test_marker_sqlmodel_extension(tmp_path):
    o = _mk(database=True, orm="sqlmodel", db_dialect="sqlite")
    write_marker(tmp_path, o, easy_fastapi_version="1.0.0", template_version="1.0.0")
    data = json.loads((tmp_path / MARKER_FILENAME).read_text(encoding="utf-8"))
    assert "orm.sqlmodel" in data["registered_extensions"]
