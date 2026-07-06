"""RedisExtension 装配测试（override）。"""

from pathlib import Path

import pytest
from easy_fastapi.core.app import EasyFastAPI
from easy_fastapi.core.persistence.memory import MemoryPersistence
from easy_fastapi.ext.redis.extension import RedisExtension
from easy_fastapi.ext.redis.persistence import RedisPersistence
from fastapi import FastAPI


def _yaml(tmp_path: Path, content: str | None = None) -> Path:
    p = tmp_path / "easy-fastapi.yaml"
    if content is None:
        content = 'fastapi:\n  root_path: /api\neasy_fastapi:\n  redis:\n    enabled: true\n    url: "redis://localhost:6379/0"\n'
    p.write_text(content, encoding="utf-8")
    return p


def test_extension_name():
    assert RedisExtension().name == "redis"


def test_extension_config_model():
    from easy_fastapi.ext.redis.config import RedisConfig

    assert RedisExtension().config_model() is RedisConfig


def test_extension_overrides_persistence(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    assert isinstance(easy.context.services["persistence"], MemoryPersistence)
    easy.use(RedisExtension())
    assert isinstance(easy.context.services["persistence"], RedisPersistence)


def test_extension_disabled_keeps_memory(tmp_path):
    p = tmp_path / "easy-fastapi.yaml"
    p.write_text("fastapi:\n  root_path: /api\neasy_fastapi:\n  redis:\n    enabled: false\n", encoding="utf-8")
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=p)
    easy.use(RedisExtension())
    assert isinstance(easy.context.services["persistence"], MemoryPersistence)


def test_extension_requires_empty():
    assert RedisExtension().requires == []


def test_extension_duplicate_use_raises(tmp_path):
    from easy_fastapi.core.exceptions import ExtensionError

    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(RedisExtension())
    with pytest.raises(ExtensionError):
        easy.use(RedisExtension())


def test_extension_config_loaded(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(RedisExtension())
    cfg = easy.context.get_config("redis")
    assert cfg is not None
    assert cfg.enabled is True


def test_extension_disabled_persistence_is_memory(tmp_path):
    p = tmp_path / "easy-fastapi.yaml"
    p.write_text("fastapi:\n  root_path: /api\neasy_fastapi:\n  redis:\n    enabled: false\n", encoding="utf-8")
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=p)
    easy.use(RedisExtension())
    # disabled 不 override，仍是 MemoryPersistence
    assert not isinstance(easy.context.services["persistence"], RedisPersistence)


def test_extension_config_custom_url(tmp_path):
    content = (
        "fastapi:\n  root_path: /api\neasy_fastapi:\n  redis:\n    enabled: true\n    url: redis://10.0.0.1:6380/2\n"
    )
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path, content))
    easy.use(RedisExtension())
    cfg = easy.context.get_config("redis")
    assert cfg.url == "redis://10.0.0.1:6380/2"
