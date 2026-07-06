"""跨 ORM+redis+auth 全装配集成验收。"""

from pathlib import Path

from easy_fastapi.core.app import EasyFastAPI
from easy_fastapi.core.introspection import ModelIntrospector
from easy_fastapi.core.protocols import DbSessionFactory, Persistence, UserModelProtocol
from easy_fastapi.ext.auth.extension import AuthExtension
from easy_fastapi.ext.orm.sqlalchemy.crud import SQLAlchemyCRUDMixin
from easy_fastapi.ext.orm.sqlalchemy.extension import SQLAlchemyExtension
from easy_fastapi.ext.redis.extension import RedisExtension
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import DeclarativeBase


class _Base(DeclarativeBase):
    pass


class User(_Base, SQLAlchemyCRUDMixin):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), unique=True, nullable=True)
    email = Column(String(64), unique=True, nullable=True)
    hashed_password = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)

    @property
    def identity(self):
        return self.username or self.email

    @property
    def h_pwd(self):
        return self.hashed_password

    @property
    def scopes(self):
        return []


class Role(_Base, SQLAlchemyCRUDMixin):
    __tablename__ = "role"
    id = Column(Integer, primary_key=True)
    role = Column(String(16), unique=True)
    role_desc = Column(String(32))

    @classmethod
    async def get_by_role(cls, role):
        return None

    @classmethod
    async def create_role(cls, role, role_desc, **extra):
        pass


_MODELS = [User, Role]


def _yaml(tmp_path: Path) -> Path:
    p = tmp_path / "easy-fastapi.yaml"
    p.write_text(
        "fastapi:\n  root_path: /api\n"
        "easy_fastapi:\n"
        '  database:\n    dialect: sqlite\n    database: ":memory:"\n'
        "  redis:\n    enabled: false\n"
        '  auth:\n    secret: "kXXXXXXXXXXXXXXX"\n',
        encoding="utf-8",
    )
    return p


def _yaml_file_db(tmp_path: Path) -> Path:
    """文件 sqlite（:memory: 在 async 多连接下表不共享，端到端测试用文件库）。"""
    db = tmp_path / "integ.db"
    db_str = str(db).replace("\\", "/")  # YAML 里反斜杠是转义符，用正斜杠
    p = tmp_path / "easy_fastapi_file.yaml"
    p.write_text(
        "fastapi:\n  root_path: /api\n"
        "easy_fastapi:\n"
        f'  database:\n    dialect: sqlite\n    database: "{db_str}"\n'
        "  redis:\n    enabled: false\n"
        '  auth:\n    secret: "kXXXXXXXXXXXXXXX"\n',
        encoding="utf-8",
    )
    return p


def test_full_assembly_registers_all_services(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=_MODELS)).use(RedisExtension()).use(AuthExtension())
    s = easy.context.services
    assert isinstance(s["db_session_factory"], DbSessionFactory)
    assert isinstance(s["model_introspector"], ModelIntrospector)
    assert isinstance(s["user_model"], UserModelProtocol)
    assert isinstance(s["persistence"], Persistence)
    assert "token_service" in s


def test_full_assembly_mounts_auth_routes(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml_file_db(tmp_path))
    easy.use(SQLAlchemyExtension(models=_MODELS)).use(AuthExtension())
    with TestClient(app) as client:
        resp = client.post("/auth/login", data={"username": "x", "password": "y"})
    assert resp.status_code == 401  # 路由存在，无此用户 → 401


def test_full_assembly_persistence_is_memory(tmp_path):
    """redis disabled → persistence 保留 MemoryPersistence。"""
    from easy_fastapi.core.persistence.memory import MemoryPersistence

    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=_MODELS)).use(RedisExtension())
    assert isinstance(easy.context.services["persistence"], MemoryPersistence)


def test_full_assembly_config_loaded(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=_MODELS)).use(RedisExtension()).use(AuthExtension())
    assert easy.context.get_config("auth") is not None


def test_full_assembly_auth_login_reachable(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=_MODELS)).use(AuthExtension())
    schema = app.openapi()
    assert "/auth/token" in schema.get("paths", {})
    assert "/auth/login" in schema.get("paths", {})


def test_full_assembly_refresh_and_logout_reachable(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=_MODELS)).use(AuthExtension())
    schema = app.openapi()
    paths = schema.get("paths", {})
    assert "/auth/refresh" in paths
    assert "/auth/logout" in paths
