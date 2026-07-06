"""脚手架选项契约。

单一真相源：向导→校验→manifest→renderer 全程传递。
注意：已删除 app_name（用 project_name/package_name 双轨）。
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class CreateOptions(BaseModel):
    """efa create 的全部选项。extra='forbid' 拒绝未知字段。"""

    model_config = ConfigDict(extra="forbid")

    project_name: str
    package_name: str
    in_place: bool = False
    language: Literal["zh", "en"] = "zh"

    frontend: bool = False

    static: bool = False

    database: bool = False
    orm: Literal["tortoise", "sqlalchemy", "sqlmodel"] | None = None
    db_dialect: Literal["mysql", "postgres", "sqlite"] | None = None

    migration: bool = False
    auth: bool = False
    redis: bool = False
    i18n: bool = False
