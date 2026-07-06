"""ModelIntrospector 驱动的 CRUD 代码生成（Jinja2 模板版）——Core 侧。

输入 ModelMeta → 产 router/schema/service。冲突报错不静默。
生成的代码调用 ExtendedCRUD 统一接口（by_id/paginate/create/update_from_dict/delete_by_ids），
在任意 ORM 项目均可运行。
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from easy_fastapi.core.introspection import ModelMeta
from easy_fastapi.project import resolve_db_config

from .conflict import GenConflictError

_TEMPLATES_DIR = Path(__file__).parent / "templates" / "codegen"

_TYPE_MAP = {
    # Tortoise 字段类名
    "IntField": "int",
    "BigIntField": "int",
    "SmallIntField": "int",
    "CharField": "str",
    "BooleanField": "bool",
    "DatetimeField": "datetime",
    "DateField": "date",
    "TimeField": "time",
    "TextField": "str",
    "FloatField": "float",
    "DecimalField": "Decimal",
    "JSONField": "dict",
    "UUIDField": "UUID",
    "BinaryField": "bytes",
    "EnumField": "str",
    # SQLAlchemy/SQLModel 类型名（type(col.type).__name__）
    "Integer": "int",
    "BigInteger": "int",
    "SmallInteger": "int",
    "Boolean": "bool",
    "String": "str",
    "Text": "str",
    "DateTime": "datetime",
    "Date": "date",
    "Time": "time",
    "Float": "float",
    "Numeric": "Decimal",
    "JSON": "dict",
    "UUID": "UUID",
    "LargeBinary": "bytes",
    "Enum": "str",
    # Python 类型别名（小写）
    "int": "int",
    "str": "str",
    "bool": "bool",
    "float": "float",
    "datetime": "datetime",
    "date": "date",
    "time": "time",
    "Decimal": "Decimal",
    "bytes": "bytes",
    "dict": "dict",
    "json": "dict",
    "varchar": "str",
    "text": "str",
}


def _snake(name: str) -> str:
    """CamelCase → snake_case（正确处理连续大写如 UserID→user_id、APIKey→api_key）。"""
    import re

    # 先在「连续大写 + 后续小写」边界插入下划线：UserID → User_ID
    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    # 再在「小写/数字 + 大写」边界插入：userID → user_ID
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


def _make_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _append_export(init_path: Path, line: str) -> None:
    """向 __init__.py 幂等追加一行导出。

    - 文件不存在：创建并写入该行
    - 已存在且该行已在文件中：不重复追加（幂等，按行精确匹配）
    - 已存在但无该行：保留原内容，末尾补换行后追加
    """
    init_path.parent.mkdir(parents=True, exist_ok=True)
    if init_path.exists():
        content = init_path.read_text(encoding="utf-8")
        existing_lines = content.splitlines()
        if line in existing_lines:
            return
        if content and not content.endswith("\n"):
            content += "\n"
        content += line + "\n"
    else:
        content = line + "\n"
    init_path.write_text(content, encoding="utf-8")


def generate_for_model(meta: ModelMeta, *, project_dir: Path, force: bool = False) -> list[Path]:
    """按 ModelMeta 生成 schema/service/router 三文件。

    目标已存在且 force=False 时抛 GenConflictError。
    生成后幂等追加各包 __init__.py 导出。
    """
    project_dir = Path(project_dir)
    snake = _snake(meta.name)
    env = _make_env()
    # 提取主键信息供模板使用（不再硬编码 id: int）
    pk_fields = [f for f in meta.fields if f.primary_key]
    if len(pk_fields) > 1:
        raise ValueError(f"模型 {meta.name} 有复合主键，codegen 暂不支持：{[f.name for f in pk_fields]}")
    pk_name = pk_fields[0].name if pk_fields else "id"
    pk_type = _TYPE_MAP.get(pk_fields[0].type_name, "int") if pk_fields else "int"
    # 未知类型检测：防止静默降级为 str 导致运行时类型错误
    unknown = {f.type_name for f in meta.fields if f.type_name not in _TYPE_MAP}
    if unknown:
        raise ValueError(f"模型 {meta.name} 包含不支持的字段类型：{unknown}（可在 _TYPE_MAP 中注册）")
    # 收集模板需要的额外 import
    used_types = {_TYPE_MAP[f.type_name] for f in meta.fields}
    ctx = {
        "meta": meta,
        "snake": snake,
        "type_map": _TYPE_MAP,
        "pk_name": pk_name,
        "pk_type": pk_type,
        "needs_datetime": "datetime" in used_types,
        "needs_date": "date" in used_types,
        "needs_time": "time" in used_types,
        "needs_decimal": "Decimal" in used_types,
        "needs_uuid": "UUID" in used_types,
    }

    targets = {
        project_dir / "app" / "schemas" / f"{snake}.py": env.get_template("schema.py.j2").render(**ctx),
        project_dir / "app" / "services" / f"{snake}.py": env.get_template("service.py.j2").render(**ctx),
        project_dir / "app" / "routers" / f"{snake}_router.py": env.get_template("router.py.j2").render(**ctx),
    }
    if not force:
        existing = [str(p) for p in targets if p.exists()]
        if existing:
            raise GenConflictError(f"目标文件已存在：{existing}（使用 --force 覆盖）")
    written = []
    for path, content in targets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)

    # 幂等追加 __init__.py 导出
    _append_export(project_dir / "app" / "schemas" / "__init__.py", f"from .{snake} import *")
    _append_export(project_dir / "app" / "services" / "__init__.py", f"from . import {snake}")
    _append_export(project_dir / "app" / "routers" / "__init__.py", f"from .{snake}_router import {snake}_router")

    return written


def _get_introspector(orm: str):
    """按 orm 名称取 introspector 实例（lazy import 避免顶层拖入重型依赖）。"""
    if orm == "tortoise":
        from easy_fastapi.ext.orm.tortoise.introspector import TortoiseModelIntrospector

        return TortoiseModelIntrospector()
    if orm == "sqlalchemy":
        from easy_fastapi.ext.orm.sqlalchemy.introspector import SQLAlchemyModelIntrospector

        return SQLAlchemyModelIntrospector()
    if orm == "sqlmodel":
        from easy_fastapi.ext.orm.sqlmodel.introspector import SQLModelIntrospector

        return SQLModelIntrospector()
    raise ValueError(f"不支持的 ORM：{orm}")


def _collect_sa_style_models(orm: str, module_paths: list[str]) -> list[type]:
    """import 项目模型模块，收集 SQLAlchemy/SQLModel 模型类。

    SQLAlchemy 风格 introspector 需要已加载的模型类列表（读 __table__.columns）。
    SQLModel 从 SQLModel.metadata 收集；SQLAlchemy 从模块属性找 DeclarativeBase 子类。
    """
    import importlib

    imported = [importlib.import_module(m) for m in module_paths]
    if orm == "sqlmodel":
        from sqlmodel import SQLModel

        return [
            m
            for m in SQLModel.metadata.registry._class_registry.values()  # type: ignore[attr-defined]
            if isinstance(m, type)
            and issubclass(m, SQLModel)
            and m is not SQLModel
            and getattr(m, "__tablename__", None) is not None
        ]
    # sqlalchemy
    from sqlalchemy.orm import DeclarativeBase

    models: list[type] = []
    for mod in imported:
        for attr in vars(mod).values():
            try:
                if (
                    isinstance(attr, type)
                    and issubclass(attr, DeclarativeBase)
                    and attr is not DeclarativeBase
                    and getattr(attr, "__tablename__", None) is not None
                ):
                    models.append(attr)
            except TypeError:
                continue
    return models


def _init_for_introspection(orm: str, ctx: dict) -> None:
    """按需初始化 ORM 运行时，使 introspector 能从注册表提取模型元数据。

    tortoise 的 introspector 依赖 Tortoise.apps 注册表，必须先 init；
    sqlalchemy/sqlmodel 的 introspector 直接读 __table__.columns，需要先 import
    项目模型模块让 metadata 填充，并收集模型类传入 introspector。
    """
    if orm == "tortoise":
        import asyncio

        from easy_fastapi.ext.orm.tortoise.session import init_tortoise

        asyncio.run(init_tortoise(db_url=ctx["db_url"], models=ctx["models"]))
        return
    # sqlalchemy / sqlmodel：import 模型模块，收集模型类
    ctx["model_classes"] = _collect_sa_style_models(orm, ctx["models"])


def run_gen(project_dir: Path, *, force: bool = False) -> None:
    """完整 gen 流程：读 marker+yaml → 初始化 ORM → 取 introspector → 对每个模型 generate_for_model。"""
    orm, db_url, models, app_dir = resolve_db_config(project_dir)
    ctx: dict = {"orm": orm, "db_url": db_url, "models": models, "app_dir": app_dir}
    _init_for_introspection(orm, ctx)
    introspector = _get_introspector(orm)
    # SA/SQLModel 风格 introspector 需要显式传入模型类列表
    if "model_classes" in ctx:
        metas = introspector.extract_models(models=ctx["model_classes"])
    else:
        metas = introspector.extract_models()
    if not metas:
        return
    for meta in metas:
        generate_for_model(meta, project_dir=app_dir, force=force)
