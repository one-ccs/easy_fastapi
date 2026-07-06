"""build_manifest migration/auth/redis/static 片段测试（≥8 用例）。"""

from easy_fastapi_cli.scaffold.manifest import build_manifest
from easy_fastapi_cli.scaffold.options import CreateOptions


def _mk(**kw):
    base = {
        "project_name": "demo",
        "package_name": "demo",
        "database": True,
        "orm": "tortoise",
        "db_dialect": "mysql",
    }
    base.update(kw)
    return CreateOptions(**base)


# ── 1. migration + tortoise → aerich ──


def test_migration_aerich_when_tortoise():
    m = build_manifest(_mk(migration=True))
    assert "aerich" in m.dependencies


# ── 2. migration + sqlalchemy → alembic ──


def test_migration_alembic_when_sqlalchemy():
    m = build_manifest(_mk(orm="sqlalchemy", migration=True))
    assert "alembic" in m.dependencies


# ── 3. migration + sqlmodel → alembic ──


def test_migration_alembic_when_sqlmodel():
    m = build_manifest(_mk(orm="sqlmodel", migration=True))
    assert "alembic" in m.dependencies


# ── 4. migration=False 不加迁移依赖 ──


def test_no_migration_dep_when_false():
    m = build_manifest(_mk(migration=False))
    assert "aerich" not in m.dependencies
    assert "alembic" not in m.dependencies


# ── 5. auth 加 pwdlib + pyjwt + 路由片段 ──


def test_auth_adds_pwdlib_pyjwt_and_routes():
    m = build_manifest(_mk(auth=True))
    deps = " ".join(m.dependencies)
    assert "pwdlib" in deps
    assert "pyjwt" in deps
    dests = " ".join(f.dest for f in m.fragments)
    assert "auth" in dests


# ── 6. auth 触发 post_messages ──


def test_post_messages_present_when_auth():
    m = build_manifest(_mk(auth=True))
    assert len(m.post_messages) > 0


# ── 7. redis 加 redis 依赖但不再生成 redis_config ──


def test_redis_adds_redis_dep():
    m = build_manifest(_mk(redis=True))
    assert "redis" in m.dependencies
    dests = " ".join(f.dest for f in m.fragments)
    assert "app/core/redis_config.py" not in dests


# ── 8. static 仅写入 yaml 配置，不生成静态文件 ──


def test_static_adds_static_fragment():
    m = build_manifest(_mk(database=False, orm=None, static=True))
    dests = [f.dest for f in m.fragments]
    # static 走 StaticExtension（yaml 配置），不再生成 mount.py / index.html
    assert "static/index.html" not in dests
    assert "app/core/static_mount.py" not in dests
    # static 配置由 easy-fastapi.yaml.j2 渲染（运行时由 StaticExtension 加载）
    assert any(f.src.endswith("easy-fastapi.yaml.j2") for f in m.fragments)


# ── 9. auth 片段含 handler 但不再生成 auth_config ──


def test_auth_fragments_full():
    m = build_manifest(_mk(auth=True))
    dests = " ".join(f.dest for f in m.fragments)
    assert "app/handlers/auth_handler.py" in dests
    assert "app/core/auth_config.py" not in dests


# ── 10. frontend 触发 post_messages ──


def test_post_messages_present_when_frontend():
    m = build_manifest(_mk(frontend=True))
    joined = " ".join(m.post_messages)
    assert "前端" in joined or "pnpm" in joined


# ── 11. 无 auth 无 frontend 时 post_messages 含 uv sync 但不含 pnpm ──


def test_no_post_messages_when_minimal():
    m = build_manifest(_mk())
    joined = " ".join(m.post_messages)
    assert "uv sync" in joined
    assert "pnpm" not in joined


# ── 12. auth=False 不加认证依赖/片段 ──


def test_no_auth_when_false():
    m = build_manifest(_mk(auth=False))
    assert "pwdlib" not in m.dependencies
    dests = {f.dest for f in m.fragments}
    # auth=False 时不生成 auth 相关业务文件
    assert "app/routers/auth.py" not in dests
    assert "app/handlers/auth_handler.py" not in dests
    assert "app/core/auth_config.py" not in dests
