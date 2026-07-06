"""E2E: 生成项目 + codegen 新模型 + CRUD 端到端。

严格按 /loop 指令要求真实运行验证：
1. 生成 Tortoise + SQLite + auth 项目
2. 用 generate_for_model 生成 Article 的 schema/service/router
3. 注入 Article 模型 + 注册路由
4. 启动 TestClient，验证 CRUD 端到端可运行

覆盖：注册→登录→获取 token→POST 创建→GET 查询→/page 分页→PUT 修改→DELETE 删除。
"""

import importlib
import sys
from importlib.resources import files
from pathlib import Path

from easy_fastapi.commands.gen import generate_for_model
from easy_fastapi.core.introspection import FieldMeta, ModelMeta
from easy_fastapi_cli.scaffold.conflict import check_target
from easy_fastapi_cli.scaffold.manifest import build_manifest
from easy_fastapi_cli.scaffold.marker import write_marker
from easy_fastapi_cli.scaffold.options import CreateOptions
from easy_fastapi_cli.scaffold.validate import apply_defaults, validate
from easy_fastapi_cli.scaffold.write import write_manifest


def _create_tortoise_auth_project(tmp_path: Path, name: str) -> Path:
    """生成 Tortoise + SQLite + auth 项目（程序 API）。"""
    o = apply_defaults(
        CreateOptions(
            project_name=name,
            package_name=name,
            database=True,
            orm="tortoise",
            db_dialect="sqlite",
            auth=True,
        )
    )
    o = validate(o)
    project_dir = tmp_path / name
    check_target(project_dir, in_place=False)
    project_dir.mkdir(parents=True)
    templates_root = Path(str(files("easy_fastapi_cli") / "templates"))
    manifest = build_manifest(o, templates_root=templates_root)
    write_manifest(manifest, o, project_dir, templates_root)
    write_marker(project_dir, o, easy_fastapi_version="1.0.0", template_version="1.0.0")
    return project_dir


_ARTICLE_META = ModelMeta(
    name="Article",
    fields=[
        FieldMeta(name="id", type_name="IntField", primary_key=True, nullable=False, relation=None),
        FieldMeta(name="title", type_name="CharField", primary_key=False, nullable=False, relation=None),
        FieldMeta(name="content", type_name="TextField", primary_key=False, nullable=True, relation=None),
    ],
)

_ARTICLE_MODEL_SRC = '''"""Article 模型（E2E 测试注入）。"""
from __future__ import annotations

from tortoise import Model, fields

from easy_fastapi.ext.orm.tortoise.crud import ExtendedCRUD


class Article(Model, ExtendedCRUD):  # type: ignore[misc, valid-type]
    """文章表。"""

    id = fields.IntField(primary_key=True, description="文章 id")
    title = fields.CharField(max_length=128, description="标题")
    content = fields.TextField(null=True, description="内容")

    class Meta:
        table = "article"


__all__ = ["Article"]
'''


def _inject_article(project_dir: Path) -> None:
    """写入 Article 模型文件并接入 models/__init__.py 导出。"""
    models_dir = project_dir / "app" / "models"
    (models_dir / "article.py").write_text(_ARTICLE_MODEL_SRC, encoding="utf-8")
    init_path = models_dir / "__init__.py"
    text = init_path.read_text(encoding="utf-8")
    if "from .article import Article as Article" not in text:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "from .article import Article as Article\n"
        init_path.write_text(text, encoding="utf-8")


def _register_article_router(project_dir: Path) -> None:
    """在 bootstrap/routers.py 的 register_routers 内追加 article 路由注册。"""
    routers_path = project_dir / "app" / "bootstrap" / "routers.py"
    text = routers_path.read_text(encoding="utf-8")
    register_block = (
        "\n    # E2E: 注册 article 路由\n"
        "    from app.routers.article_router import article_router\n"
        '    app.include_router(article_router, prefix="/article", tags=["文章"])\n'
    )
    if "article_router" not in text:
        # 在 register_routers 函数体的 include_router 块之后追加
        # 模板可能用 tags=["角色"]（硬编码）或 tags=[_("Role")]（i18n）
        role_line = None
        for pattern in (
            'app.include_router(role_router, prefix="/role", tags=[_("Role")])',
            'app.include_router(role_router, prefix="/role", tags=["角色"])',
        ):
            if pattern in text:
                role_line = pattern
                break
        if role_line:
            text = text.replace(role_line, role_line + register_block)
        routers_path.write_text(text, encoding="utf-8")


def _load_app(project_dir: Path):
    """动态 import 生成项目的 app.main:app。需要 CWD 在项目根目录。"""
    import os

    prev_cwd = Path.cwd()
    sys.path.insert(0, str(project_dir))
    os.chdir(project_dir)
    try:
        for mod in list(sys.modules):
            if mod == "app" or mod.startswith("app."):
                del sys.modules[mod]
        mod = importlib.import_module("app.main")
        return mod.app
    finally:
        os.chdir(prev_cwd)
        sys.path.remove(str(project_dir))


def _setup_file_db(project_dir: Path) -> None:
    """用文件数据库替代 :memory:（Tortoise 0.25.x :memory: 每连接独立，TestClient 跨连接失败）。"""
    yaml_path = project_dir / "easy-fastapi.yaml"
    yaml_text = yaml_path.read_text(encoding="utf-8")
    db_path = str(project_dir / "test.db").replace("\\", "/")
    yaml_text = yaml_text.replace('database: ":memory:"', f'database: "{db_path}"')
    yaml_path.write_text(yaml_text, encoding="utf-8")


def _patch_main_to_include_article(project_dir: Path) -> None:
    """修改生成项目的 app/extensions/orm.py，让 TortoiseExtension 扫描 Article 模型。

    默认 TortoiseExtension 只扫描 user/role 模型；
    E2E 需要让 Tortoise init 也注册 Article 表。
    """
    orm_path = project_dir / "app" / "extensions" / "orm.py"
    text = orm_path.read_text(encoding="utf-8")
    # 顶部追加 Article import
    text = text.replace(
        "from app.models.role import Role\n",
        "from app.models.role import Role\nfrom app.models.article import Article\n",
        1,
    )
    # 在 TortoiseExtension(models=[User, Role]) 后追加 Article
    text = text.replace(
        "TortoiseExtension(models=[User, Role])",
        "TortoiseExtension(models=[User, Role, Article])",
    )
    orm_path.write_text(text, encoding="utf-8")


def _provision_project(tmp_path: Path, name: str) -> Path:
    """完整装配一个含 Article CRUD 的可运行项目。"""
    project_dir = _create_tortoise_auth_project(tmp_path, name)
    # codegen 生成 schema/service/router 三文件 + __init__ 接线
    generate_for_model(_ARTICLE_META, project_dir=project_dir, force=True)
    # 注入 Article 模型 + 注册路由
    _inject_article(project_dir)
    _register_article_router(project_dir)
    _patch_main_to_include_article(project_dir)
    _setup_file_db(project_dir)
    return project_dir


# ── 产物存在性 ──


def test_codegen_creates_article_files(tmp_path):
    project_dir = _provision_project(tmp_path, "e2e_files")
    assert (project_dir / "app" / "schemas" / "article.py").exists()
    assert (project_dir / "app" / "services" / "article.py").exists()
    assert (project_dir / "app" / "routers" / "article_router.py").exists()


def test_codegen_wires_init_exports(tmp_path):
    project_dir = _provision_project(tmp_path, "e2e_wires")
    schemas_init = (project_dir / "app" / "schemas" / "__init__.py").read_text(encoding="utf-8")
    services_init = (project_dir / "app" / "services" / "__init__.py").read_text(encoding="utf-8")
    routers_init = (project_dir / "app" / "routers" / "__init__.py").read_text(encoding="utf-8")
    assert "from .article import *" in schemas_init
    assert "from . import article" in services_init
    assert "from .article_router import article_router" in routers_init


def test_codegen_article_model_injected(tmp_path):
    project_dir = _provision_project(tmp_path, "e2e_model")
    models_init = (project_dir / "app" / "models" / "__init__.py").read_text(encoding="utf-8")
    assert "from .article import Article as Article" in models_init
    assert (project_dir / "app" / "models" / "article.py").exists()


# ── 应用可装配 ──


def test_app_importable_after_codegen(tmp_path):
    project_dir = _provision_project(tmp_path, "e2e_import")
    fastapi_app = _load_app(project_dir)
    assert fastapi_app is not None


def test_article_routes_registered(tmp_path):
    """article 路由可达性：用真实 HTTP 请求验证端点已挂载（非 import 时直接查 app.routes，
    FastAPI include_router 产出 _IncludedRouter 懒对象，路径在路由树构建时才解析）。"""
    from fastapi.testclient import TestClient

    project_dir = _provision_project(tmp_path, "e2e_routes")
    fastapi_app = _load_app(project_dir)
    with TestClient(fastapi_app) as client:
        # 受保护端点无 token 应返回 401（证明路由存在，只是未授权）
        assert client.post("/article", json={"title": "x"}).status_code == 401
        assert client.get("/article/page").status_code == 401
        # 未知路径才返回 404
        assert client.get("/article-nonexistent").status_code == 404


# ── 端到端 CRUD 全流程 ──


def test_article_crud_end_to_end(tmp_path):
    """完整 CRUD：注册→登录→创建→查询→分页→修改→删除。"""
    from fastapi.testclient import TestClient

    project_dir = _provision_project(tmp_path, "e2e_crud")
    fastapi_app = _load_app(project_dir)
    with TestClient(fastapi_app) as client:
        # 健康检查
        assert client.get("/health").status_code == 200

        # 注册 + 登录拿 token
        assert client.post("/users/register", json={"username": "writer", "password": "secret123"}).status_code == 201
        r = client.post("/auth/login", data={"username": "writer", "password": "secret123"})
        assert r.status_code == 200
        token = r.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 无 token 访问受保护端点 → 401
        assert client.post("/article", json={"title": "noauth"}).status_code == 401

        # 创建
        r = client.post("/article", json={"title": "hello", "content": "world"}, headers=headers)
        assert r.status_code == 200, r.text
        created = r.json()["data"]
        assert created["title"] == "hello"
        assert created["content"] == "world"
        assert created["id"] is not None
        art_id = created["id"]

        # 查询单条
        r = client.get("/article", params={"id": art_id}, headers=headers)
        assert r.status_code == 200
        assert r.json()["data"]["title"] == "hello"

        # 查询不存在
        r = client.get("/article", params={"id": 99999}, headers=headers)
        assert r.status_code in (400, 404)

        # 分页
        r = client.get("/article/page", params={"page": 1, "size": 10}, headers=headers)
        assert r.status_code == 200
        page_data = r.json()["data"]
        assert page_data["total"] == 1
        assert len(page_data["items"]) == 1

        # 修改
        r = client.put("/article", json={"id": art_id, "title": "updated"}, headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["title"] == "updated"

        # 删除
        r = client.delete("/article", params={"ids": [art_id]}, headers=headers)
        assert r.status_code == 200
        assert r.json()["data"] == 1

        # 删除后查不到
        r = client.get("/article", params={"id": art_id}, headers=headers)
        assert r.status_code in (400, 404)

        # 删除空列表
        r = client.delete("/article", params={"ids": [99999]}, headers=headers)
        assert r.status_code == 200
        assert r.json()["data"] == 0


def test_article_delete_multiple_and_count(tmp_path):
    """批量创建→批量删除返回正确数量。"""
    from fastapi.testclient import TestClient

    project_dir = _provision_project(tmp_path, "e2e_multi")
    fastapi_app = _load_app(project_dir)
    with TestClient(fastapi_app) as client:
        assert client.post("/users/register", json={"username": "admin", "password": "secret123"}).status_code == 201
        r = client.post("/auth/login", data={"username": "admin", "password": "secret123"})
        token = r.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        ids = []
        for i in range(3):
            r = client.post("/article", json={"title": f"t{i}"}, headers=headers)
            ids.append(r.json()["data"]["id"])

        # 分页应见 3 条
        r = client.get("/article/page", params={"page": 1, "size": 10}, headers=headers)
        assert r.json()["data"]["total"] == 3

        # 批量删除
        r = client.delete("/article", params={"ids": ids}, headers=headers)
        assert r.status_code == 200
        assert r.json()["data"] == 3

        # 删完
        r = client.get("/article/page", params={"page": 1, "size": 10}, headers=headers)
        assert r.json()["data"]["total"] == 0
        assert r.json()["data"]["finished"] is True


def test_article_pagination_finished_flag(tmp_path):
    """分页 finished 标志：单页内 finished=True，跨页时首页 finished=False。"""
    from fastapi.testclient import TestClient

    project_dir = _provision_project(tmp_path, "e2e_page")
    fastapi_app = _load_app(project_dir)
    with TestClient(fastapi_app) as client:
        assert client.post("/users/register", json={"username": "pager", "password": "secret123"}).status_code == 201
        r = client.post("/auth/login", data={"username": "pager", "password": "secret123"})
        token = r.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        for i in range(5):
            client.post("/article", json={"title": f"t{i}"}, headers=headers)

        # page_size=2：首页 total=5, 5 > 2*1 → finished=False
        r = client.get("/article/page", params={"page": 1, "size": 2}, headers=headers)
        page_data = r.json()["data"]
        assert page_data["total"] == 5
        assert len(page_data["items"]) == 2
        assert page_data["finished"] is False

        # 第三页 page_size=2：5 <= 2*3 → finished=True
        r = client.get("/article/page", params={"page": 3, "size": 2}, headers=headers)
        assert r.json()["data"]["finished"] is True


def test_article_create_validation_missing_required_field(tmp_path):
    """缺必填字段 title → 400 校验错误（EasyFastAPI 将 RequestValidationError 映射为 400）。"""
    from fastapi.testclient import TestClient

    project_dir = _provision_project(tmp_path, "e2e_valid")
    fastapi_app = _load_app(project_dir)
    with TestClient(fastapi_app) as client:
        reg = client.post("/users/register", json={"username": "validator", "password": "secret123"})
        assert reg.status_code == 201
        r = client.post("/auth/login", data={"username": "validator", "password": "secret123"})
        token = r.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # title 必填（CharField 非 nullable），缺字段应 400（框架统一拦截 validation error）
        r = client.post("/article", json={"content": "no title"}, headers=headers)
        assert r.status_code == 400
