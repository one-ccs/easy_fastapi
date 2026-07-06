"""响应码策略——分离 JSON body code 与 HTTP status_code。

两种内置模式：
- "http"：code = HTTP status（RESTful 约定，默认）
- "zero_success"：成功 code=0，错误 code 仍用 HTTP status（中国传统业务码）

通过 set_strategy(style) 切换；EasyFastAPI._init_app 从配置段自动调用。
"""

from __future__ import annotations

from typing import Literal


class ResponseCodeStrategy:
    """默认策略：body code == HTTP status_code（RESTful 约定）。"""

    def success_code(self, status_code: int) -> int:
        return status_code

    def error_code(self, status_code: int) -> int:
        return status_code

    def http_status_for(self, code: int, *, default: int = 200) -> int:
        """从 body code 反推 HTTP status（用于显式传 code、未传 status_code 的场景）。"""
        return code if 100 <= code < 600 else default


class ZeroSuccessStrategy(ResponseCodeStrategy):
    """中国传统业务码：成功=0，错误=HTTP status。"""

    def success_code(self, status_code: int) -> int:
        return 0

    def error_code(self, status_code: int) -> int:
        return status_code

    def http_status_for(self, code: int, *, default: int = 200) -> int:
        return default if code == 0 else code


# ── 模块级策略（EasyFastAPI._init_app 根据配置设置）──

_strategy: ResponseCodeStrategy = ResponseCodeStrategy()
_trace_id_enabled: bool = False


def set_strategy(style: Literal["http", "zero_success"]) -> None:
    """根据配置切换全局策略。"""
    global _strategy
    if style == "zero_success":
        _strategy = ZeroSuccessStrategy()
    else:
        _strategy = ResponseCodeStrategy()


def get_strategy() -> ResponseCodeStrategy:
    """取当前策略（result.py / handlers.py 消费）。"""
    return _strategy


def set_trace_id(enabled: bool) -> None:
    """根据配置设置 trace_id 开关。"""
    global _trace_id_enabled
    _trace_id_enabled = enabled


def is_trace_id_enabled() -> bool:
    """取当前 trace_id 开关（result.py 消费）。"""
    return _trace_id_enabled
