"""ORM 无关共享层：通用结果模型、dialect→driver 映射、URL 构造器、CRUD 协议。"""

from easy_fastapi.ext.orm.base.crud import BaseCRUDMixin
from easy_fastapi.ext.orm.base.db_config import OrmName, build_db_url

__all__ = ["BaseCRUDMixin", "OrmName", "build_db_url"]
