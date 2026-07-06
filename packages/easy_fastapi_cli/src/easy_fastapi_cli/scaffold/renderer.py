"""纯 Jinja2 渲染器。

只渲染字符串——不读写文件系统，不做冲突检查（那些在命令层）。
StrictUndefined：未定义变量直接报错（拒绝静默空渲染）。
"""

from datetime import datetime, timezone

from jinja2 import Environment, StrictUndefined

from .options import CreateOptions
from .paths import project_layout


class Renderer:
    """Jinja2 渲染器，注入 options/layout/generated_at。"""

    def __init__(
        self,
        options: CreateOptions,
    ):
        self._options = options
        self._layout = project_layout(options)
        self._env = Environment(
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
            variable_start_string="{{",
            variable_end_string="}}",
        )

    def render(self, template_str: str) -> str:
        """渲染模板字符串，注入全局上下文变量。"""
        ctx: dict = {
            "options": self._options,
            "layout": self._layout,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        return self._env.from_string(template_str).render(**ctx)
