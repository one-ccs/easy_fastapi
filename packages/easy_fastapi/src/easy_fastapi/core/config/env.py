"""env 覆盖层。

主规则：EFA_<SECTION>__<FIELD>（双下划线分路径，支持多层嵌套）。
env 是覆盖层不替代 yaml；本地用 yaml，生产用 env 覆盖敏感项。
值转换规则见 _coerce_env_value（先 json.loads，失败保留字符串）。
"""

import copy
import json
from collections.abc import Mapping
from typing import Any

ENV_PREFIX = "EFA_"
ENV_SEP = "__"


def _coerce_env_value(value: str) -> Any:
    """env value 先尝试 json.loads，失败保留原字符串。"""
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return value


def _set_nested(target: dict, path: list[str], value: Any) -> None:
    cur = target
    for key in path[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            if nxt is not None:
                import warnings

                warnings.warn(f"env overlay: key '{key}' 的非 dict 值被覆盖为嵌套路径让路", stacklevel=2)
            nxt = {}
            cur[key] = nxt
        cur = nxt
    cur[path[-1]] = value


def apply_env_overlay(raw: dict, environ: Mapping[str, str]) -> dict:
    """按 EFA_<SECTION>__<FIELD> 把环境变量注入 raw dict 的副本。"""
    merged = copy.deepcopy(raw)
    for key, value in environ.items():
        if not key.startswith(ENV_PREFIX):
            continue
        path = key[len(ENV_PREFIX) :].lower().split(ENV_SEP)
        _set_nested(merged, path, _coerce_env_value(value))
    return merged
