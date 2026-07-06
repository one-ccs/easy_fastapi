"""codegen __init__.py 幂等追加导出测试（schemas / services / routers）。"""

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


# ── B5: schemas/__init__.py ──


def test_schemas_init_appends_export(tmp_path):
    """生成后 schemas/__init__.py 含 article 导出。"""
    generate_for_model(_meta(), project_dir=tmp_path, force=False)
    init_content = (tmp_path / "app" / "schemas" / "__init__.py").read_text(encoding="utf-8")
    assert "from .article import" in init_content


def test_schemas_init_idempotent(tmp_path):
    """重复生成不重复追加。"""
    generate_for_model(_meta(), project_dir=tmp_path, force=True)
    generate_for_model(_meta(), project_dir=tmp_path, force=True)
    init_content = (tmp_path / "app" / "schemas" / "__init__.py").read_text(encoding="utf-8")
    assert init_content.count("from .article import") == 1


def test_schemas_init_preserves_existing_content(tmp_path):
    """追加时保留已有内容。"""
    init_path = tmp_path / "app" / "schemas" / "__init__.py"
    init_path.parent.mkdir(parents=True, exist_ok=True)
    init_path.write_text("from .user import *\n", encoding="utf-8")

    generate_for_model(_meta(), project_dir=tmp_path, force=False)
    init_content = init_path.read_text(encoding="utf-8")
    assert "from .user import *" in init_content
    assert "from .article import" in init_content


def test_schemas_init_multiple_models(tmp_path):
    """多模型追加各自导出。"""
    generate_for_model(_meta("Article"), project_dir=tmp_path, force=False)
    generate_for_model(_meta("Comment"), project_dir=tmp_path, force=False)
    init_content = (tmp_path / "app" / "schemas" / "__init__.py").read_text(encoding="utf-8")
    assert "from .article import" in init_content
    assert "from .comment import" in init_content


def test_schemas_init_uses_wildcard_import(tmp_path):
    """schema 导出用通配符（from .article import *）。"""
    generate_for_model(_meta(), project_dir=tmp_path, force=False)
    init_content = (tmp_path / "app" / "schemas" / "__init__.py").read_text(encoding="utf-8")
    assert "from .article import *" in init_content


def test_schemas_init_appended_after_file_write(tmp_path):
    """导出行追加发生在文件写入之后（__init__.py 存在）。"""
    generate_for_model(_meta(), project_dir=tmp_path, force=False)
    assert (tmp_path / "app" / "schemas" / "__init__.py").exists()
    assert (tmp_path / "app" / "schemas" / "article.py").exists()


def test_schemas_init_content_ends_with_newline(tmp_path):
    """追加后 __init__.py 末尾应有换行。"""
    generate_for_model(_meta(), project_dir=tmp_path, force=False)
    init_content = (tmp_path / "app" / "schemas" / "__init__.py").read_text(encoding="utf-8")
    assert init_content.endswith("\n")


# ── B6: services & routers __init__.py ──


def test_services_init_appends_export(tmp_path):
    generate_for_model(_meta(), project_dir=tmp_path, force=False)
    init_content = (tmp_path / "app" / "services" / "__init__.py").read_text(encoding="utf-8")
    assert "from . import article" in init_content


def test_services_init_idempotent(tmp_path):
    generate_for_model(_meta(), project_dir=tmp_path, force=True)
    generate_for_model(_meta(), project_dir=tmp_path, force=True)
    init_content = (tmp_path / "app" / "services" / "__init__.py").read_text(encoding="utf-8")
    assert init_content.count("from . import article") == 1


def test_services_init_multiple_models(tmp_path):
    generate_for_model(_meta("Article"), project_dir=tmp_path, force=False)
    generate_for_model(_meta("Comment"), project_dir=tmp_path, force=False)
    init_content = (tmp_path / "app" / "services" / "__init__.py").read_text(encoding="utf-8")
    assert "from . import article" in init_content
    assert "from . import comment" in init_content


def test_routers_init_appends_export(tmp_path):
    generate_for_model(_meta(), project_dir=tmp_path, force=False)
    init_content = (tmp_path / "app" / "routers" / "__init__.py").read_text(encoding="utf-8")
    assert "from .article_router import article_router" in init_content


def test_routers_init_idempotent(tmp_path):
    generate_for_model(_meta(), project_dir=tmp_path, force=True)
    generate_for_model(_meta(), project_dir=tmp_path, force=True)
    init_content = (tmp_path / "app" / "routers" / "__init__.py").read_text(encoding="utf-8")
    assert init_content.count("from .article_router import article_router") == 1


def test_routers_init_multiple_models(tmp_path):
    generate_for_model(_meta("Article"), project_dir=tmp_path, force=False)
    generate_for_model(_meta("Comment"), project_dir=tmp_path, force=False)
    init_content = (tmp_path / "app" / "routers" / "__init__.py").read_text(encoding="utf-8")
    assert "from .article_router import article_router" in init_content
    assert "from .comment_router import comment_router" in init_content
