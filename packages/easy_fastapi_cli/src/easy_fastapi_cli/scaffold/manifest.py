"""脚手架清单契约。

Fragment: 单个文件拷贝/渲染单元。
Manifest: build_manifest 的产物——聚合所有 fragment + 依赖 + 后置提示。

模板组织（v1.0 重组后）：
- templates/backend/base/backend/  — 后端骨架（walk_tree 遍历 + 条件过滤）
- templates/backend/{orm}/backend/ — ORM 专属模型（按 options.orm 选一套遍历）
- templates/frontend/{base,pnpm}/ — 前端（walk_tree 遍历，仅 fullstack）
- templates/.gitignore.j2 / README.md.j2 / pyproject.toml.j2 — 根级文件

fullstack 模式下模板树 = 生成结果树（backend/base/backend/... → backend/...）；
backend-only 模式下 walk_tree 产出去掉 backend/ 前缀（backend/base/backend/app/... → app/...）。
"""

from pathlib import Path

from pydantic import BaseModel, Field

from .options import CreateOptions
from .paths import project_layout


class Fragment(BaseModel):
    """单个模板/拷贝单元。

    src: 模板树内相对路径
    dest: 落盘相对路径
    is_template: True=jinja 渲染；False=原样拷贝
    """

    src: str
    dest: str
    is_template: bool = True


class Manifest(BaseModel):
    """build_manifest 的产物：聚合 fragments + 依赖 + 后置提示。"""

    fragments: list[Fragment] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    dev_dependencies: list[str] = Field(default_factory=list)
    post_messages: list[str] = Field(default_factory=list)


# ── 条件过滤表（相对于 backend/ 的 dest 路径）──

# 仅 auth 时生成的文件
_AUTH_ONLY: set[str] = {
    "app/routers/auth.py",
    "app/routers/user.py",
    "app/routers/role.py",
    "app/routers/__init__.py",
    "app/schemas/user.py",
    "app/schemas/role.py",
    "app/schemas/page_query.py",
    "app/schemas/__init__.py",
    "app/services/user.py",
    "app/services/role.py",
    "app/services/__init__.py",
    "app/handlers/auth_handler.py",
    "app/extensions/auth.py",
    "test/test_auth_router.py",
    "test/conftest.py",
}

# 仅 database + orm 时生成的文件
_DB_ONLY: set[str] = {
    "app/models/__init__.py",
    "app/extensions/orm.py",
}

# 仅 redis 时生成的文件
_REDIS_ONLY: set[str] = {
    "app/extensions/redis.py",
}

# 仅 static 时生成的文件
_STATIC_ONLY: set[str] = {
    "app/extensions/static.py",
}

# 仅 i18n 时生成的文件
_I18N_ONLY: set[str] = {
    "app/extensions/i18n.py",
    "locales/zh_CN/LC_MESSAGES/messages.po",
}

# 仅 migration + orm≠tortoise 时生成的文件
_ALEMBIC_ONLY: set[str] = {
    "alembic/env.py",
    "alembic/script.py.mako",
}

# 仅 migration + orm=tortoise 时生成的文件
_AERICH_ONLY: set[str] = {
    "pyproject.toml.aerich",
}


def _should_include(rel_dest: str, options: CreateOptions) -> bool:
    """判断 base/backend/ 下的文件是否应包含在当前组合中。

    rel_dest: 相对于 backend/ 的路径（如 app/routers/auth.py）。
    """
    if rel_dest in _AUTH_ONLY and not options.auth:
        return False
    if rel_dest in _DB_ONLY and not (options.database and options.orm):
        return False
    if rel_dest in _REDIS_ONLY and not options.redis:
        return False
    if rel_dest in _STATIC_ONLY and not options.static:
        return False
    if rel_dest in _I18N_ONLY and not options.i18n:
        return False
    if rel_dest in _ALEMBIC_ONLY and not (options.migration and options.orm and options.orm != "tortoise"):
        return False
    if rel_dest in _AERICH_ONLY and not (options.migration and options.orm == "tortoise"):
        return False
    return True


def _strip_backend_prefix(dest: str, layout: str) -> str:
    """backend-only 模式去掉 backend/ 前缀。

    fullstack: 模板树内已有 backend/ 前缀，dest 不变（落盘到 backend/...）。
    backend-only: 去掉 backend/ 前缀（落盘到项目根，而非 backend/）。
    """
    if layout == "backend-only" and dest.startswith("backend/"):
        return dest[len("backend/") :]
    return dest


# ORM 真实 PyPI 包名
_ORM_PACKAGE = {
    "tortoise": "tortoise-orm",
    "sqlalchemy": "sqlalchemy",
    "sqlmodel": "sqlmodel",
}

# dialect → 异步驱动（与 ext/orm/base 一致）
_DRIVER_FOR = {
    "mysql": "asyncmy",
    "postgres": "asyncpg",
    "sqlite": "aiosqlite",
}


def build_manifest(options: CreateOptions, *, templates_root: Path | None = None) -> Manifest:
    """按 options 组装清单。

    templates_root: 模板根目录（遍历模式需要）；默认用 importlib.resources 定位。
    """
    if templates_root is None:
        from importlib.resources import files

        templates_root = Path(str(files("easy_fastapi_cli") / "templates"))

    m = Manifest()
    layout = project_layout(options)
    from .walk import walk_tree  # 延迟导入：walk.py 依赖本模块的 Fragment，顶层导入会循环

    # ── 根级文件（不经 layout 前缀处理）──
    _add_root_files(m, options)

    # ── 后端骨架（walk_tree 遍历 backend/base/backend/ + 条件过滤）──
    base_be = templates_root / "backend" / "base" / "backend"
    if base_be.exists():
        for frag in walk_tree(base_be, dest_prefix="backend/", templates_root=templates_root):
            # frag.dest 形如 "backend/app/routers/auth.py"；取相对 backend/ 的路径做条件判断
            rel = frag.dest.removeprefix("backend/")
            if not _should_include(rel, options):
                continue
            frag.dest = _strip_backend_prefix(frag.dest, layout)
            m.fragments.append(frag)

    # ── ORM 模型（walk_tree 遍历选中的 orm 子树）──
    _add_orm(m, options, layout, templates_root, walk_tree)

    # ── 根级 README（fullstack workspace 根，仅 fullstack）──
    if options.frontend:
        m.fragments.append(Fragment(src="README.md.j2", dest="README.md"))

    # ── 前端（不变）──
    if options.frontend:
        fe_root = templates_root / "frontend"
        if fe_root.exists():
            for sub in ("base", "pnpm"):
                sub_root = fe_root / sub
                if sub_root.exists():
                    m.fragments.extend(walk_tree(sub_root, dest_prefix="", templates_root=templates_root))

    # ── 依赖 ──
    _add_dependencies(m, options)

    m.post_messages = _build_post_messages(options)
    return m


# ── 根级文件 ──


def _add_root_files(m: Manifest, options: CreateOptions) -> None:
    """根级文件：.gitignore（两种模式）+ workspace pyproject（fullstack only）。

    package.json / pnpm-workspace.yaml / .npmrc 已在 frontend/pnpm/ 子树内，
    由 walk_tree 遍历产出。
    """
    m.fragments.append(Fragment(src=".gitignore.j2", dest=".gitignore"))
    if options.frontend:
        m.fragments.append(Fragment(src="pyproject.toml.j2", dest="pyproject.toml"))


# ── ORM 模型 ──


def _add_orm(
    m: Manifest,
    options: CreateOptions,
    layout: str,
    templates_root: Path,
    walk_tree,
) -> None:
    """ORM 专属模型文件（按 options.orm 选一套遍历）。"""
    if not options.database or options.orm is None:
        return
    orm = options.orm
    orm_root = templates_root / "backend" / orm / "backend"
    if orm_root.exists():
        for frag in walk_tree(orm_root, dest_prefix="backend/", templates_root=templates_root):
            frag.dest = _strip_backend_prefix(frag.dest, layout)
            m.fragments.append(frag)


# ── 依赖 ──


def _add_dependencies(m: Manifest, options: CreateOptions) -> None:
    """聚合所有依赖声明。"""
    # 后端骨架核心依赖
    m.dependencies.extend(["fastapi", "uvicorn", "pydantic", "pydantic-settings", "easy-pyoc"])

    # ORM
    if options.database and options.orm:
        m.dependencies.append(_ORM_PACKAGE[options.orm])
        if options.db_dialect:
            m.dependencies.append(_DRIVER_FOR[options.db_dialect])

    # migration
    if options.migration and options.orm:
        if options.orm == "tortoise":
            m.dependencies.append("aerich")
        else:
            m.dependencies.append("alembic")

    # auth
    if options.auth:
        m.dependencies.extend(["pwdlib", "pyjwt", "email-validator"])

    # redis
    if options.redis:
        m.dependencies.append("redis")

    # 测试
    m.dev_dependencies.extend(["pytest", "httpx"])


# ── 快速指南 ──


def _build_post_messages(options: CreateOptions) -> list[str]:
    """按 options.language 返回结构化快速指南。"""
    if options.language == "zh":
        return _post_messages_zh(options)
    return _post_messages_en(options)


def _post_messages_zh(options: CreateOptions) -> list[str]:
    msgs = ["项目已创建，下一步："]
    if options.frontend:
        msgs.append("  uv sync")
        if options.database:
            msgs.append("  efa db sync                  # 同步数据库 schema")
        msgs.append("  efa run --reload             # 启动后端 http://localhost:8000")
        msgs.append("  pnpm install")
        msgs.append("  pnpm sdk:gen                 # 生成 API SDK（需先启动后端）")
    else:
        msgs.append("  uv sync")
        if options.database:
            msgs.append("  efa db sync                  # 同步数据库 schema")
        msgs.append("  efa run                      # 启动后端 http://localhost:8000")
    if options.auth:
        msgs.append("  # 认证已启用：请创建首位管理员用户")
    if options.i18n:
        msgs.append("  # 国际化已启用：编辑 .po 文件后需编译 .mo")
        msgs.append("  efa i18n compile              # 编译 .po → .mo")
    return msgs


def _post_messages_en(options: CreateOptions) -> list[str]:
    msgs = ["Project created! Next steps:"]
    if options.frontend:
        msgs.append("  uv sync")
        if options.database:
            msgs.append("  efa db sync                  # sync database schema")
        msgs.append("  efa run --reload             # start backend http://localhost:8000")
        msgs.append("  pnpm install")
        msgs.append("  pnpm sdk:gen                 # generate API SDK (start backend first)")
    else:
        msgs.append("  uv sync")
        if options.database:
            msgs.append("  efa db sync                  # sync database schema")
        msgs.append("  efa run                      # start backend http://localhost:8000")
    if options.auth:
        msgs.append("  # Auth enabled: create the first admin user")
    if options.i18n:
        msgs.append("  # i18n enabled: compile .mo after editing .po files")
        msgs.append("  efa i18n compile              # compile .po → .mo")
    return msgs
