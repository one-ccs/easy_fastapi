"""static 扩展配置。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class StaticConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    directory: str = "static"
    url_path: str = "/static"

    @field_validator("url_path")
    @classmethod
    def _url_path_must_start_with_slash(cls, v: str) -> str:
        """FastAPI mount 要求路径以 / 开头，否则 ValueError。"""
        if not v.startswith("/"):
            raise ValueError(f"url_path 必须以 '/' 开头（当前：'{v}'）")
        return v
