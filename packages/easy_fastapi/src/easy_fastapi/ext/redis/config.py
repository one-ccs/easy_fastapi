"""Redis 扩展配置。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RedisConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    url: str = "redis://localhost:6379/0"
