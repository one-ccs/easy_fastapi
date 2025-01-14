#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Final, Optional, Any
from pathlib import Path
from datetime import timedelta

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator
from easy_pyoc import PathUtil, YAMLUtil, ObjectUtil

from .logger import uvicorn_logger


CONFIG_PATH: Final[str] = PathUtil.abspath('easy_fastapi.yaml')


def safe_folder(folder: Optional[str]) -> str:
    if not folder:
        return ''

    p = Path(folder)

    _p = p.absolute().as_posix()
    # 是否在程序运行目录下
    if not p.is_relative_to(PathUtil.get_work_dir()):
        uvicorn_logger.warning(f'资源目录 "{_p}" 不是在程序运行目录下，可能导致文件权限问题')

    return _p


# easy_fastapi 配置

class Authorization(BaseModel):
    """授权配置类"""
    secret_key: Optional[str] = None                                  # 认证密钥
    algorithm: str = 'HS256'                                          # 认证加密算法
    access_token_expire_minutes: timedelta = timedelta(minutes=15)    # 访问令牌过期时间
    refresh_token_expire_minutes: timedelta = timedelta(60 * 24 * 7)  # 刷新令牌过期时间

    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            uvicorn_logger.error('认证密钥未设置')
        elif len(v) < 16:
            uvicorn_logger.warning('认证密钥长度过短，建议长度至少为 16 位')
        elif v in {'easy_fastapi', '123456', 'pass'}:
            uvicorn_logger.warning('认证密钥不安全，建议使用复杂密码')
        return v

    @field_serializer('access_token_expire_minutes')
    def serialize_access_token_expire_minutes(self, t: int) -> timedelta:
        return timedelta(minutes=t)

    @field_serializer('refresh_token_expire_minutes')
    def serialize_refresh_token_expire_minutes(self, t: int) -> timedelta:
        return timedelta(minutes=t)


class Resources(BaseModel):
    """资源配置类"""
    upload_folder: Optional[str] = None     # 上传文件目录
    templates_folder: Optional[str] = None  # 模板文件目录
    static_folder: Optional[str] = None     # 静态资源目录
    static_name: Optional[str] = None       # 静态资源名称
    static_url: Optional[str] = None        # 静态资源 URL

    @property
    def is_template(self) -> bool:
        """是否启用模板"""
        return bool(self.templates_folder)

    @property
    def is_static(self) -> bool:
        """是否启用静态资源"""
        return bool(self.static_folder and self.static_name and self.static_url)

    @field_serializer('upload_folder')
    def serialize_upload_folder(self, upload_folder: Optional[str]) -> str:
        return safe_folder(upload_folder)

    @field_serializer('templates_folder')
    def serialize_templates_folder(self, templates_folder: Optional[str]) -> str:
        return safe_folder(templates_folder)

    @field_serializer('static_folder')
    def serialize_static_folder(self, static_folder: Optional[str]) -> Optional[str]:
        return safe_folder(static_folder)


class EasyFastAPI(BaseModel):
    """EasyFastAPI 配置类"""
    force_success_code: bool = False  # 是否强制返回 200 状态码
    authorization: Authorization = Authorization()
    resources: Resources = Resources()


# fastapi 配置

class Contact(BaseModel):
    """联系人配置类"""
    name: str = 'one-ccs'               # 联系人名称
    url: Optional[str] = None           # 联系人 URL
    email: str = 'one-ccs@foxmail.com'  # 联系人邮箱


class License(BaseModel):
    """许可证配置类"""
    name: str = ''             # 许可证名称
    url: Optional[str] = None  # 许可证 URL


class Swagger(BaseModel):
    """Swagger 配置类"""
    title: str = 'Easy FastAPI'         # 文档标题
    description: str = ''               # 文档描述
    version: str = '0.1.0'              # 文档版本
    contact: Contact = Contact()
    license: License = License()
    token_url: str = '/token'           # 访问令牌 URL
    docs_url: str = '/docs'             # 文档 URL
    redoc_url: str = '/redoc'           # 文档 URL
    openapi_url: str = '/openapi.json'  # OpenAPI 文档 URL


class CORS(BaseModel):
    """CORS 配置类"""
    enabled: bool = False                     # 是否启用跨域
    allow_origin_regex: Optional[str] = None  # 允许跨域的源正则
    allow_origins: list[str] = ['*']          # 允许跨域的源
    allow_methods: list[str] = ['*']          # 允许跨域的请求方法
    allow_headers: list[str] = ['*']          # 允许跨域的请求头
    allow_credentials: bool = True            # 是否允许跨域带上 cookie
    expose_headers: list[str] = []            # 跨域请求暴露的头
    max_age: int = 600                        # 跨域有效期（秒）


class HTTPSRedirect(BaseModel):
    """HTTPS 重定向配置类"""
    enabled: bool = False  # 是否启用 HTTPS 重定向


class TrustedHost(BaseModel):
    """信任主机配置类"""
    enabled: bool = False           # 是否启用信任主机
    allowed_hosts: list[str] = ['*']  # 信任的主机列表


class GZip(BaseModel):
    """GZip 配置类"""
    enabled: bool = False     # 是否启用 GZip
    minimum_size: int = 1000  # 压缩最小字节数
    compress_level: int = 5   # 压缩级别


class Middleware(BaseModel):
    """中间件配置类"""
    cors: CORS = CORS()
    https_redirect: HTTPSRedirect = HTTPSRedirect()
    trusted_host: TrustedHost = TrustedHost()
    gzip: GZip = GZip()


class FastAPI(BaseModel):
    """FastAPI 配置类"""
    root_path: str = '/'  # 根路径
    swagger: Swagger = Swagger()
    middleware: Middleware = Middleware()


# database 配置

class Database(BaseModel):
    """数据库配置类"""
    username: Optional[str] = None    # 数据库用户名
    password: Optional[str] = None    # 数据库密码
    database: Optional[str] = None    # 数据库名称
    host: str = '127.0.0.1'           # 数据库主机
    port: int = 3306                  # 数据库端口
    echo: bool = False                # 是否打印 SQL 语句
    timezone: str = 'Asia/Chongqing'  # 时区

    @property
    def uri(self) -> str:
        """生成数据库连接 URI"""
        if not self.username or not self.password or not self.database:
            uvicorn_logger.error('数据库用户名、密码、数据库名称不能为空')

        return f"mysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            uvicorn_logger.error('数据库用户名未设置')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            uvicorn_logger.error('数据库密码未设置')
        return v

    @field_validator('database')
    @classmethod
    def validate_database(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            uvicorn_logger.error('数据库名称未设置')
        return v


# redis 配置

class Redis(BaseModel):
    enabled: bool = False           # 是否启用 Redis
    host: Optional[str] = None      # Redis 主机
    port: int = 6379                # Redis 端口
    password: Optional[str] = None  # Redis 密码
    db: int = 0                     # Redis 数据库
    decode_responses: bool = True   # 是否解码 Redis 响应数据


class Config(BaseModel):
    """配置类，用于获取配置文件中的配置项"""
    model_config = ConfigDict(
        extra='allow',
    )

    easy_fastapi: EasyFastAPI = EasyFastAPI()
    fastapi: FastAPI = FastAPI()
    database: Database = Database()
    redis: Redis = Redis()

    def get_config(self, key_path: str, default: Any = None) -> Any:
        """获取配置项"""
        return ObjectUtil.get_value_from_dict(self.__dict__, key_path, default)


try:
    config = Config(**(YAMLUtil.load(CONFIG_PATH) or {}))
except FileNotFoundError:
    config = Config()
    uvicorn_logger.debug(f'配置文件 "{CONFIG_PATH}" 不存在，使用默认配置')
except Exception as e:
    config = Config()
    uvicorn_logger.error(f'配置文件 "{CONFIG_PATH}" 加载失败，使用默认配置，错误信息：\n{e}')
