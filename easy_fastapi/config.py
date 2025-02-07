#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import TypeVar, ClassVar, Final, Optional
from pathlib import Path
from datetime import timedelta

from pydantic import (
    BaseModel as _BaseModel,
    ConfigDict,
    ValidationInfo,
    field_serializer,
    field_validator,
    computed_field,
)
from easy_pyoc import (
    Magic,
    PathUtil,
    YAMLUtil,
    ObjectUtil,
    ExceptionUtil,
)

from .logger import logger


T = TypeVar('T')

CONFIG_PATH: Final[str] = PathUtil.abspath('easy_fastapi.yaml')


def safe_dir(path: Optional[str]) -> str:
    if not path:
        return ''

    p = Path(path)

    _p = p.absolute().as_posix()
    # 是否在程序运行目录下
    if not p.is_relative_to(PathUtil.get_work_dir()):
        logger.warning(f'资源目录 "{_p}" 不是在程序运行目录下，可能导致文件权限问题')

    return _p

class BaseModel(Magic, _BaseModel): ...

# easy_fastapi 配置

class Authentication(BaseModel):
    """认证配置类"""
    secret_key: str = 'easy_fastapi'                                          # 认证密钥
    iss: str = 'easy_fastapi'                                                 # 令牌签发者
    token_url: str = '/auth/token'                                            # 认证令牌 URL
    refresh_url: str = '/auth/refresh'                                        # 刷新令牌 URL
    login_url: str = '/auth/login'                                            # 登录 URL
    logout_url: str = '/auth/logout'                                          # 登出 URL
    register_url: str = '/auth/register'                                      # 注册 URL
    algorithm: str = 'HS256'                                                  # 认证加密算法
    access_token_expire_minutes: timedelta = timedelta(minutes=15)            # 访问令牌过期时间
    refresh_token_expire_minutes: timedelta = timedelta(minutes=60 * 24 * 7)  # 刷新令牌过期时间

    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v: Optional[str]) -> Optional[str]:
        if len(v) < 16:
            logger.warning('认证密钥长度过短，建议长度至少为 16 位')
        elif v in {'easy_fastapi', '123456', 'pass'}:
            logger.warning('认证密钥不安全，建议使用复杂密码')
        return v

    @field_serializer('access_token_expire_minutes')
    def serialize_access_token_expire_minutes(self, t: int) -> timedelta:
        return timedelta(minutes=t)

    @field_serializer('refresh_token_expire_minutes')
    def serialize_refresh_token_expire_minutes(self, t: int) -> timedelta:
        return timedelta(minutes=t)


class SPA(BaseModel):
    """单页应用配置类"""
    index_file: Optional[str] = None        # 入口文件名
    static_dir: Optional[str] = None        # 静态资源目录
    static_url: Optional[str] = None        # 静态资源 URL
    enabled: bool = False                   # 是否挂载单页应用

    @field_validator('enabled')
    @classmethod
    def validate_enabled(cls, v: bool, values: ValidationInfo) -> bool:
        if v and (not values.data.get('index_file') or not values.data.get('static_dir') or not values.data.get('static_url')):
            raise ValueError('单页应用配置不完整')
        return v

    @field_validator('index_file')
    @classmethod
    def validate_index_file(cls, v: Optional[str]) -> Optional[str]:
        if v and not PathUtil.is_exists_file(v):
            raise ValueError(f'入口文件 "{v}" 不存在')
        return v

    @field_serializer('static_dir')
    def serialize_static_dir(self, static_dir: Optional[str]) -> Optional[str]:
        return safe_dir(static_dir)


class EasyFastAPI(BaseModel):
    """EasyFastAPI 配置类"""
    force_success_code: bool = False  # 是否强制返回 200 状态码
    upload_dir: Optional[str] = None  # 上传文件目录
    spa: SPA = SPA()
    authentication: Authentication = Authentication()

    @field_serializer('upload_dir')
    def serialize_upload_dir(self, upload_dir: Optional[str]) -> str:
        return safe_dir(upload_dir)


# fastapi 配置

class Contact(BaseModel):
    """联系人配置类"""
    name: str = 'one-ccs'               # 联系人名称
    url: Optional[str] = None           # 联系人 URL
    email: str = 'one-ccs@foxmail.com'  # 联系人邮箱


class License(BaseModel):
    """许可证配置类"""
    name: str = ''                      # 许可证名称
    url: Optional[str] = None           # 许可证 URL


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
    allow_origin_regex: Optional[str] = None  # 允许跨域的源正则
    allow_origins: list[str] = ['*']          # 允许跨域的源
    allow_methods: list[str] = ['*']          # 允许跨域的请求方法
    allow_headers: list[str] = ['*']          # 允许跨域的请求头
    allow_credentials: bool = True            # 是否允许跨域带上 cookie
    expose_headers: list[str] = []            # 跨域请求暴露的头
    max_age: int = 600                        # 跨域有效期（秒）
    enabled: bool = False                     # 是否启用跨域


class HTTPSRedirect(BaseModel):
    """HTTPS 重定向配置类"""
    enabled: bool = False  # 是否启用 HTTPS 重定向


class TrustedHost(BaseModel):
    """信任主机配置类"""
    allowed_hosts: list[str] = ['*']  # 信任的主机列表
    enabled: bool = False           # 是否启用信任主机


class GZip(BaseModel):
    """GZip 配置类"""
    minimum_size: int = 1000  # 压缩最小字节数
    compress_level: int = 5   # 压缩级别
    enabled: bool = False     # 是否启用 GZip


class Middleware(BaseModel):
    """中间件配置类"""
    cors: CORS = CORS()
    https_redirect: HTTPSRedirect = HTTPSRedirect()
    trusted_host: TrustedHost = TrustedHost()
    gzip: GZip = GZip()


class FastAPI(BaseModel):
    """FastAPI 配置类"""
    root_path: str = ''  # 根路径
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

    @computed_field
    @property
    def uri(self) -> str:
        """生成数据库连接 URI"""
        if not self.username or not self.password or not self.database:
            raise ValueError('数据库用户名、密码、数据库名称不能为空')

        return f'mysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}'


# redis 配置

class Redis(BaseModel):
    host: Optional[str] = None      # Redis 主机
    port: int = 6379                # Redis 端口
    password: Optional[str] = None  # Redis 密码
    db: int = 0                     # Redis 数据库
    decode_responses: bool = True   # 是否解码 Redis 响应数据
    enabled: bool = False           # 是否启用 Redis


class Config(BaseModel):
    """配置类，用于获取配置文件中的配置项"""
    _instance: ClassVar[Optional['Config']] = None

    model_config = ConfigDict(
        extra='allow',
    )

    easy_fastapi: EasyFastAPI = EasyFastAPI()
    fastapi: FastAPI = FastAPI()
    database: Database = Database()
    redis: Redis = Redis()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            try:
                logger.info(f'从文件 "{CONFIG_PATH}" 加载配置')
                config = YAMLUtil.load(CONFIG_PATH) or {}
                super().__init__(cls._instance, **config)
                logger.debug(f'配置内容：{cls._instance}')
            except FileNotFoundError:
                logger.warning(f'配置文件 "{CONFIG_PATH}" 不存在，使用默认配置')
            except:
                exc_msg = ExceptionUtil.get_message()
                logger.debug(f'配置文件 "{CONFIG_PATH}" 加载失败，使用默认配置，错误信息：\n{exc_msg}')

        return cls._instance

    def __init__(self): ...

    def get(self, key_path: str, default: Optional[T] = None) -> Optional[T]:
        """获取配置项"""
        return ObjectUtil.get_value_from_dict(self.__dict__, key_path, default)
