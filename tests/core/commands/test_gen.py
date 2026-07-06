"""Core commands/gen 执行逻辑单测。

覆盖：generate_for_model（纯 codegen：三文件/冲突/--force/snake_case）、
run_gen（完整流程：无数据库报错/写文件/--force 覆盖）。
introspector 用 FakeIntrospector 替换，避免真实导入 ORM。

yaml-driven：run_gen 经 resolve_db_config 读 yaml 取真实 db_url；
marker 旁写 easy-fastapi.yaml 的 database 段。
"""

import json

import pytest
from easy_fastapi.core.config.loader import _clear_config_cache
from easy_fastapi.core.exceptions import ConfigError
from easy_fastapi.core.introspection import FieldMeta, ModelMeta

MARKER_FILENAME = ".easy-fastapi.json"


def _write_marker(tmp_path, *, orm="tortoise", database=True):
    data = {
        "marker_schema_version": 1,
        "project_layout": "backend-only",
        "options": {"orm": orm, "db_dialect": "sqlite", "database": database},
        "registered_extensions": [f"orm.{orm}"] if database and orm else [],
    }
    (tmp_path / MARKER_FILENAME).write_text(json.dumps(data), encoding="utf-8")


def _write_yaml(app_dir, *, dialect="sqlite", database=":memory:"):
    app_dir.mkdir(parents=True, exist_ok=True)
    lines = ["easy_fastapi:", "  database:", f'    dialect: "{dialect}"']
    if dialect == "sqlite":
        lines.append(f'    database: "{database}"')
    (app_dir / "easy-fastapi.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture(autouse=True)
def _clear_cache():
    _clear_config_cache()
    yield
    _clear_config_cache()


def _meta(name="Article"):
    return ModelMeta(
        name=name,
        fields=[
            FieldMeta(name="id", type_name="IntField", primary_key=True, nullable=False, relation=None),
            FieldMeta(name="title", type_name="CharField", primary_key=False, nullable=False, relation=None),
        ],
    )


class FakeIntrospector:
    _DEFAULT = object()

    def __init__(self, metas=_DEFAULT):
        self._metas = [_meta()] if metas is FakeIntrospector._DEFAULT else metas

    def extract_models(self, models_path=None, **kw):
        return self._metas


# ── generate_for_model（纯 codegen 测试）──


def test_generate_creates_three_files(tmp_path):
    from easy_fastapi.commands.gen import generate_for_model

    files = generate_for_model(_meta(), project_dir=tmp_path, force=False)
    assert len(files) == 3
    rel_paths = {p.relative_to(tmp_path).as_posix() for p in files}
    assert "app/schemas/article.py" in rel_paths
    assert "app/services/article.py" in rel_paths
    assert "app/routers/article_router.py" in rel_paths


def test_generate_conflict_raises(tmp_path):
    from easy_fastapi.commands.conflict import GenConflictError
    from easy_fastapi.commands.gen import generate_for_model

    generate_for_model(_meta(), project_dir=tmp_path, force=False)
    with pytest.raises(GenConflictError):
        generate_for_model(_meta(), project_dir=tmp_path, force=False)


def test_generate_force_overwrites(tmp_path):
    from easy_fastapi.commands.gen import generate_for_model

    generate_for_model(_meta(), project_dir=tmp_path, force=False)
    files = generate_for_model(_meta(), project_dir=tmp_path, force=True)
    assert len(files) == 3


def test_generate_snake_case_naming(tmp_path):
    from easy_fastapi.commands.gen import generate_for_model

    generate_for_model(_meta(name="UserProfile"), project_dir=tmp_path, force=False)
    assert (tmp_path / "app" / "schemas" / "user_profile.py").exists()
    assert (tmp_path / "app" / "services" / "user_profile.py").exists()
    assert (tmp_path / "app" / "routers" / "user_profile_router.py").exists()


def test_generate_writes_init_exports(tmp_path):
    from easy_fastapi.commands.gen import generate_for_model

    generate_for_model(_meta(), project_dir=tmp_path, force=False)
    schemas_init = (tmp_path / "app" / "schemas" / "__init__.py").read_text(encoding="utf-8")
    services_init = (tmp_path / "app" / "services" / "__init__.py").read_text(encoding="utf-8")
    routers_init = (tmp_path / "app" / "routers" / "__init__.py").read_text(encoding="utf-8")
    assert "from .article import *" in schemas_init
    assert "from . import article" in services_init
    assert "from .article_router import article_router" in routers_init


def test_generate_init_export_substring_idempotency(tmp_path):
    """生成 user 后再生成 user_profile，__init__.py 不因子串匹配跳过。"""
    from easy_fastapi.commands.gen import generate_for_model

    generate_for_model(_meta(name="User"), project_dir=tmp_path, force=True)
    schemas_init = tmp_path / "app" / "schemas" / "__init__.py"
    assert "from .user import *" in schemas_init.read_text(encoding="utf-8")
    # 生成 user_profile —— 如果用子串匹配会误判已存在
    generate_for_model(_meta(name="UserProfile"), project_dir=tmp_path, force=True)
    content = schemas_init.read_text(encoding="utf-8")
    assert "from .user import *" in content
    assert "from .user_profile import *" in content


# ── run_gen（完整 gen 流程）──


def test_run_gen_no_database_raises(tmp_path):
    _write_marker(tmp_path, orm=None, database=False)
    from easy_fastapi.commands.gen import run_gen

    with pytest.raises(ConfigError):
        run_gen(tmp_path)


def test_run_gen_writes_files(tmp_path, monkeypatch):
    _write_marker(tmp_path)
    _write_yaml(tmp_path)
    from easy_fastapi.commands import gen as genmod

    monkeypatch.setattr(genmod, "_get_introspector", lambda orm: FakeIntrospector())
    monkeypatch.setattr(genmod, "_init_for_introspection", lambda orm, ctx: None)
    genmod.run_gen(tmp_path)
    assert (tmp_path / "app" / "schemas" / "article.py").exists()


def test_run_gen_force(tmp_path, monkeypatch):
    _write_marker(tmp_path)
    _write_yaml(tmp_path)
    from easy_fastapi.commands import gen as genmod

    monkeypatch.setattr(genmod, "_get_introspector", lambda orm: FakeIntrospector())
    monkeypatch.setattr(genmod, "_init_for_introspection", lambda orm, ctx: None)
    genmod.run_gen(tmp_path)
    # 不加 force 再跑报冲突
    with pytest.raises(genmod.GenConflictError):
        genmod.run_gen(tmp_path, force=False)
    # 加 force 成功
    genmod.run_gen(tmp_path, force=True)


def test_run_gen_no_models_is_noop(tmp_path, monkeypatch):
    _write_marker(tmp_path)
    _write_yaml(tmp_path)
    from easy_fastapi.commands import gen as genmod

    monkeypatch.setattr(genmod, "_get_introspector", lambda orm: FakeIntrospector(metas=[]))
    monkeypatch.setattr(genmod, "_init_for_introspection", lambda orm, ctx: None)
    genmod.run_gen(tmp_path)  # 不抛、不写
    assert not (tmp_path / "app" / "schemas").exists()


def test_run_gen_missing_marker_raises(tmp_path):
    from easy_fastapi.commands.gen import run_gen

    with pytest.raises(ConfigError):
        run_gen(tmp_path)
