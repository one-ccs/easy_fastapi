"""配置加载器（内部设施，可注入测试）。

职责：① from_yaml 读文件（唯一 IO 点）+ 可选 env overlay；
     ② section(key, model) 按需 model_validate（按需校验，没 use 的段不加载）。
"""

import os
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, TypeVar

from yaml import safe_load

from ..exceptions import ConfigError
from .env import apply_env_overlay

if TYPE_CHECKING:
    pass

T = TypeVar("T")


class ConfigLoader:
    def __init__(self, raw: Mapping[str, Any], path: Path | None):
        self._raw = MappingProxyType(raw)
        self.path = path

    @classmethod
    def from_yaml(
        cls,
        path: Path,
        *,
        environ: Mapping[str, str] | None = None,
        apply_env: bool = True,
    ) -> "ConfigLoader":
        p = Path(path)
        if not p.exists():
            raise ConfigError(f"配置文件 '{path}' 不存在。脚手架生成的项目必须包含 easy-fastapi.yaml。")
        raw = safe_load(p.read_text(encoding="utf-8")) or {}
        if apply_env:
            raw = apply_env_overlay(raw, environ or os.environ)
        return cls(raw, p)

    def _resolve_key(self, key: str) -> Any:
        """按点分路径解析嵌套 dict，中途缺失返回 {}。"""
        cur: Any = self._raw
        for part in key.split("."):
            if not isinstance(cur, Mapping):
                return {}
            cur = cur.get(part, {})
        return cur

    def section(self, key: str, model: "type[T]") -> "T":
        """按 section key 校验为 model。

        key 支持点分路径（如 "easy_fastapi.auth"）按层遍历嵌套 dict。
        缺失段按空 dict {} 传给 model_validate——是否允许缺失由 model 的
        字段默认值/必填决定。
        """
        return model.model_validate(self._resolve_key(key))

    def has_section(self, key: str) -> bool:
        """key 支持点分路径。"""
        cur: Any = self._raw
        for part in key.split("."):
            if not isinstance(cur, Mapping):
                return False
            if part not in cur:
                return False
            cur = cur[part]
        return True


# ── 模块级缓存 + 公共 API ──

_config_cache: dict[Path, ConfigLoader] = {}


def get_config(config_path: Path | None = None) -> ConfigLoader:
    """获取 ConfigLoader（带进程级缓存）。

    config_path=None → 通过 .easy-fastapi.json 定位项目根目录，推导 yaml 路径。
    """
    if config_path is None:
        from ...project import resolve_config_path  # lazy import 避免循环依赖

        config_path = resolve_config_path()
    config_path = Path(config_path).resolve()
    if config_path not in _config_cache:
        _config_cache[config_path] = ConfigLoader.from_yaml(config_path)
    return _config_cache[config_path]


def _clear_config_cache() -> None:
    """测试 helper：清除进程级缓存。"""
    _config_cache.clear()
