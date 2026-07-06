"""codegen Jinja2 模板渲染测试。

验证 schema/service/router 三个 Jinja2 模板对 ModelMeta 的渲染：
- 含 DatetimeField 时导入 datetime（B1 修复的 bug）
- 主键类型从 type_map 取而非硬编码 int（B1 修复）
- Base/Out/Create/Modify 四类正确
- pk_name/pk_type 参数化（不再硬编码 id: int）
"""

from pathlib import Path

from easy_fastapi.core.introspection import FieldMeta, ModelMeta
from jinja2 import Environment, StrictUndefined

TEMPLATES_DIR = Path("packages/easy_fastapi/src/easy_fastapi/commands/templates/codegen")

# ORM type_name → Python 类型字符串（由 codegen 渲染层注入模板）
TYPE_MAP = {
    "IntField": "int",
    "int": "int",
    "CharField": "str",
    "varchar": "str",
    "str": "str",
    "BooleanField": "bool",
    "bool": "bool",
    "DatetimeField": "datetime",
    "datetime": "datetime",
    "DateField": "date",
    "date": "date",
    "TimeField": "time",
    "time": "time",
    "TextField": "str",
    "text": "str",
    "FloatField": "float",
    "float": "float",
    "DecimalField": "Decimal",
    "Decimal": "Decimal",
    "UUIDField": "UUID",
    "UUID": "UUID",
    "JSONField": "dict",
    "json": "dict",
}


def _default_ctx(**overrides):
    """构建模板渲染默认上下文（pk_name/pk_type/needs_* 自动推导）。"""
    meta = overrides.get("meta")
    snake = overrides.get("snake", "article")
    pk_fields = [f for f in meta.fields if f.primary_key] if meta else []
    pk_name = pk_fields[0].name if pk_fields else "id"
    pk_type = TYPE_MAP.get(pk_fields[0].type_name, "int") if pk_fields else "int"
    used_types = {TYPE_MAP.get(f.type_name, "str") for f in meta.fields} if meta else set()
    ctx = {
        "meta": meta,
        "type_map": TYPE_MAP,
        "snake": snake,
        "pk_name": pk_name,
        "pk_type": pk_type,
        "needs_datetime": "datetime" in used_types,
        "needs_date": "date" in used_types,
        "needs_time": "time" in used_types,
        "needs_decimal": "Decimal" in used_types,
        "needs_uuid": "UUID" in used_types,
    }
    ctx.update(overrides)
    return ctx


def _load_template(name: str):
    env = Environment(undefined=StrictUndefined, keep_trailing_newline=True, trim_blocks=True, lstrip_blocks=True)
    return env.from_string((TEMPLATES_DIR / name).read_text(encoding="utf-8"))


def _meta_with_datetime() -> ModelMeta:
    return ModelMeta(
        name="Event",
        fields=[
            FieldMeta(name="id", type_name="IntField", primary_key=True, nullable=False, relation=None),
            FieldMeta(name="title", type_name="CharField", primary_key=False, nullable=False, relation=None),
            FieldMeta(name="happened_at", type_name="DatetimeField", primary_key=False, nullable=True, relation=None),
        ],
    )


# ── B1: schema 模板 ──


def test_schema_template_renders_datetime_import():
    """含 DatetimeField 时必须导入 datetime。"""
    tmpl = _load_template("schema.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_with_datetime(), snake="event"))
    assert "from datetime import datetime" in rendered
    assert "happened_at: datetime | None = None" in rendered


def test_schema_template_no_datetime_when_not_needed():
    """不含 DatetimeField 时不导入 datetime。"""
    meta = ModelMeta(
        name="Article",
        fields=[
            FieldMeta(name="id", type_name="IntField", primary_key=True, nullable=False, relation=None),
            FieldMeta(name="title", type_name="CharField", primary_key=False, nullable=False, relation=None),
        ],
    )
    tmpl = _load_template("schema.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=meta, snake="article"))
    assert "from datetime import datetime" not in rendered


def test_schema_template_renders_base_class():
    tmpl = _load_template("schema.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_with_datetime(), snake="event"))
    assert "class EventBase(BaseModel):" in rendered
    assert "title: str" in rendered


def test_schema_template_renders_out_create_modify():
    tmpl = _load_template("schema.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_with_datetime(), snake="event"))
    assert "class Event(EventBase):" in rendered
    assert "class EventCreate(EventBase): ..." in rendered
    assert "class EventModify(EventBase):" in rendered
    assert "id: int" in rendered


def test_schema_template_pk_type_uses_mapping():
    """主键类型应从 type_map 取，而非硬编码 int。"""
    meta = ModelMeta(
        name="Item",
        fields=[
            FieldMeta(name="id", type_name="CharField", primary_key=True, nullable=False, relation=None),
        ],
    )
    tmpl = _load_template("schema.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=meta, snake="item"))
    assert "id: str" in rendered  # CharField PK → str，不是 int


def test_schema_template_nullable_field_has_none_default():
    tmpl = _load_template("schema.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_with_datetime(), snake="event"))
    assert "happened_at: datetime | None = None" in rendered


def test_schema_template_non_nullable_field_no_default():
    meta = ModelMeta(
        name="Article",
        fields=[
            FieldMeta(name="id", type_name="IntField", primary_key=True, nullable=False, relation=None),
            FieldMeta(name="title", type_name="CharField", primary_key=False, nullable=False, relation=None),
        ],
    )
    tmpl = _load_template("schema.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=meta, snake="article"))
    # title 非空，不带 | None 也不带默认值
    assert "title: str\n" in rendered or "title: str\r\n" in rendered


def test_schema_template_multiple_conditional_imports():
    """datetime + Decimal 同时存在时，两个 import 都应渲染（不互斥）。"""
    meta = ModelMeta(
        name="Transaction",
        fields=[
            FieldMeta(name="id", type_name="IntField", primary_key=True, nullable=False, relation=None),
            FieldMeta(name="amount", type_name="DecimalField", primary_key=False, nullable=False, relation=None),
            FieldMeta(name="created_at", type_name="DatetimeField", primary_key=False, nullable=True, relation=None),
        ],
    )
    tmpl = _load_template("schema.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=meta, snake="transaction"))
    assert "from datetime import datetime" in rendered
    assert "from decimal import Decimal" in rendered


# ── B2: service 模板 ──


def _meta_article() -> ModelMeta:
    return ModelMeta(
        name="Article",
        fields=[
            FieldMeta(name="id", type_name="IntField", primary_key=True, nullable=False, relation=None),
            FieldMeta(name="title", type_name="CharField", primary_key=False, nullable=False, relation=None),
        ],
    )


def test_service_template_renders_five_methods():
    tmpl = _load_template("service.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_article(), snake="article"))
    assert "async def get(id: int):" in rendered
    assert "async def add(data: schemas.ArticleCreate):" in rendered
    assert "async def modify(data: schemas.ArticleModify):" in rendered
    assert "async def delete(ids: list[int]):" in rendered
    assert "async def page(page_query: schemas.PageQuery):" in rendered


def test_service_template_uses_extended_crud_methods():
    """service 只调用 ExtendedCRUD 统一接口，不直接用 ORM 原生 API。"""
    tmpl = _load_template("service.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_article(), snake="article"))
    assert "models.Article.by_id" in rendered
    assert "models.Article.create(" in rendered
    assert "models.Article.update_from_dict" in rendered
    assert "models.Article.delete_by_ids" in rendered
    assert "models.Article.paginate" in rendered


def test_service_template_not_uses_orm_native_api():
    """service 不应出现 ORM 原生 save/filter/delete 调用。"""
    tmpl = _load_template("service.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_article(), snake="article"))
    assert "db.save()" not in rendered
    assert ".filter(" not in rendered
    assert "models.Article(**" not in rendered  # 用 create() 而非直接构造 + save


def test_service_template_imports_framework_symbols():
    tmpl = _load_template("service.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_article(), snake="article"))
    assert "from easy_fastapi import" in rendered
    assert "FailureException" in rendered
    assert "Result" in rendered
    assert "from app import schemas, models" in rendered


def test_service_template_not_found_raises_failure():
    tmpl = _load_template("service.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_article(), snake="article"))
    assert "FailureException('Article not found')" in rendered


def test_service_template_add_uses_create_kwargs():
    """add 应通过 create(**model_dump) 调用 ExtendedCRUD.create。"""
    tmpl = _load_template("service.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_article(), snake="article"))
    assert "await models.Article.create(**data.model_dump(exclude_unset=True))" in rendered


def test_service_template_modify_uses_update_from_dict():
    """modify 应调用 ExtendedCRUD.update_from_dict。"""
    tmpl = _load_template("service.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_article(), snake="article"))
    assert "update_from_dict(db, data.model_dump(exclude={'id'}, exclude_unset=True))" in rendered


# ── B3: router 模板 ──


def test_router_template_renders_router_var():
    tmpl = _load_template("router.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_article(), snake="article"))
    assert "article_router = APIRouter()" in rendered


def test_router_template_renders_five_endpoints():
    tmpl = _load_template("router.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_article(), snake="article"))
    assert "@article_router.get" in rendered
    assert "@article_router.post" in rendered
    assert "@article_router.put" in rendered
    assert "@article_router.delete" in rendered
    assert "/page" in rendered


def test_router_template_uses_auth_require():
    tmpl = _load_template("router.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_article(), snake="article"))
    assert "@auth.require" in rendered


def test_router_template_response_models():
    tmpl = _load_template("router.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_article(), snake="article"))
    assert "response_model=BaseResult[schemas.Article]" in rendered


def test_router_template_imports_service():
    """router 通过 from app import services 取 service 模块，避免与路由参数冲突。"""
    tmpl = _load_template("router.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_article(), snake="article"))
    assert "from app.services import article" not in rendered
    assert "from app import schemas, services" in rendered
    assert "from app.extensions.auth import auth" in rendered
    assert "services.article.get" in rendered


def test_router_template_page_endpoint_uses_depends():
    tmpl = _load_template("router.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_article(), snake="article"))
    assert "Annotated[schemas.PageQuery, Depends()]" in rendered


def test_router_template_delete_uses_query_param():
    tmpl = _load_template("router.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_article(), snake="article"))
    assert "ids: list[int] = Query(...)" in rendered


def test_router_template_all_endpoints_have_auth_require():
    """5 个端点都应带 @auth.require。"""
    tmpl = _load_template("router.py.j2")
    rendered = tmpl.render(**_default_ctx(meta=_meta_article(), snake="article"))
    assert rendered.count("@auth.require") == 5
