"""generator/codegen——ModelIntrospector 驱动 CRUD 生成测试。"""

import pytest
from easy_fastapi.commands.conflict import GenConflictError
from easy_fastapi.commands.gen import generate_for_model
from easy_fastapi.core.introspection import FieldMeta, ModelMeta


def _meta(name="Article"):
    return ModelMeta(
        name=name,
        fields=[
            FieldMeta(name="id", type_name="IntField", primary_key=True, nullable=False, relation=None),
            FieldMeta(name="title", type_name="CharField", primary_key=False, nullable=False, relation=None),
        ],
    )


# ── 1. 生成三文件 ──


def test_generate_creates_three_files(tmp_path):
    files = generate_for_model(_meta(), project_dir=tmp_path, force=False)
    assert len(files) == 3
    # schemas 与 services 下文件同名（article.py），但路径不同
    rel_paths = {p.relative_to(tmp_path).as_posix() for p in files}
    assert "app/schemas/article.py" in rel_paths
    assert "app/services/article.py" in rel_paths
    assert "app/routers/article_router.py" in rel_paths


# ── 2. 文件落在正确目录（schemas/services/routers）──


def test_generate_file_paths(tmp_path):
    generate_for_model(_meta(), project_dir=tmp_path, force=False)
    assert (tmp_path / "app" / "schemas" / "article.py").exists()
    assert (tmp_path / "app" / "services" / "article.py").exists()
    assert (tmp_path / "app" / "routers" / "article_router.py").exists()


# ── 3. schema 内容含模型名 ──


def test_generate_schema_contains_model_name(tmp_path):
    generate_for_model(_meta(), project_dir=tmp_path, force=False)
    schema = (tmp_path / "app" / "schemas" / "article.py").read_text(encoding="utf-8")
    assert "Article" in schema


# ── 4. 冲突报 GenConflictError ──


def test_generate_conflict_raises(tmp_path):
    generate_for_model(_meta(), project_dir=tmp_path, force=False)
    with pytest.raises(GenConflictError):
        generate_for_model(_meta(), project_dir=tmp_path, force=False)


# ── 5. force=True 覆盖不抛 ──


def test_generate_force_overwrites(tmp_path):
    generate_for_model(_meta(), project_dir=tmp_path, force=False)
    files = generate_for_model(_meta(), project_dir=tmp_path, force=True)
    assert len(files) == 3


# ── 6. 驼峰→snake 命名 ──


def test_generate_snake_case_naming(tmp_path):
    generate_for_model(_meta(name="UserProfile"), project_dir=tmp_path, force=False)
    assert (tmp_path / "app" / "schemas" / "user_profile.py").exists()


# ── 7. 不同模型名各自隔离 ──


def test_generate_multiple_models_isolated(tmp_path):
    generate_for_model(_meta(name="Article"), project_dir=tmp_path, force=False)
    files = generate_for_model(_meta(name="Comment"), project_dir=tmp_path, force=False)
    assert len(files) == 3
    assert (tmp_path / "app" / "schemas" / "comment.py").exists()
    # 原有 article 文件不受影响
    assert (tmp_path / "app" / "schemas" / "article.py").exists()


# ── 8. 冲突错误消息含路径提示 ──


def test_generate_conflict_message_mentions_path(tmp_path):
    generate_for_model(_meta(), project_dir=tmp_path, force=False)
    with pytest.raises(GenConflictError) as exc_info:
        generate_for_model(_meta(), project_dir=tmp_path, force=False)
    assert "article" in str(exc_info.value) or "force" in str(exc_info.value).lower()


# ── 9. 父目录自动创建 ──


def test_generate_creates_parent_dirs(tmp_path):
    # app/schemas 等目录不应预先存在
    assert not (tmp_path / "app" / "schemas").exists()
    generate_for_model(_meta(), project_dir=tmp_path, force=False)
    assert (tmp_path / "app" / "schemas").is_dir()


# ── 10. force=False 对全新目标不报错 ──


def test_generate_force_false_clean_target(tmp_path):
    files = generate_for_model(_meta(), project_dir=tmp_path, force=False)
    assert len(files) == 3


# ── 11. 多字段 schema 生成正确 ──


def test_generate_schema_multi_field(tmp_path):
    meta = ModelMeta(
        name="Article",
        fields=[
            FieldMeta(name="id", type_name="IntField", primary_key=True, nullable=False, relation=None),
            FieldMeta(name="title", type_name="CharField", primary_key=False, nullable=False, relation=None),
            FieldMeta(name="body", type_name="TextField", primary_key=False, nullable=True, relation=None),
        ],
    )
    generate_for_model(meta, project_dir=tmp_path, force=False)
    schema = (tmp_path / "app" / "schemas" / "article.py").read_text(encoding="utf-8")
    assert "title" in schema
    assert "body" in schema
