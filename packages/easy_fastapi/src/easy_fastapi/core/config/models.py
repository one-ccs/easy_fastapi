"""核心固定配置模型（fastapi 段 + easy_fastapi 核心段）。

严格模式：extra='forbid'（写错键直接报错）。ORM/Redis/Auth/Static 配置
在 easy_fastapi 段下，由各 ext 按 loader.section("easy_fastapi.<name>") 按需加载。
"""

from typing import Literal

from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict


class BaseModel(_BaseModel):
    model_config = ConfigDict(extra="forbid")


class Contact(BaseModel):
    name: str = "one-ccs"
    url: str | None = None
    email: str = "one-ccs@foxmail.com"


class License(BaseModel):
    name: str = ""
    url: str | None = None


class Swagger(BaseModel):
    title: str = "Easy FastAPI"
    description: str = ""
    version: str = "0.1.0"
    contact: Contact = Contact()
    license: License = License()
    token_url: str = "/auth/token"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"


class CORS(BaseModel):
    allow_origin_regex: str | None = None
    allow_origins: list[str] = ["*"]
    allow_methods: list[str] = ["*"]
    allow_headers: list[str] = ["*"]
    allow_credentials: bool = True
    expose_headers: list[str] = []
    max_age: int = 600
    enabled: bool = False


class HTTPSRedirect(BaseModel):
    enabled: bool = False


class TrustedHost(BaseModel):
    allowed_hosts: list[str] = ["*"]
    enabled: bool = False


class GZip(BaseModel):
    minimum_size: int = 1000
    compress_level: int = 5
    enabled: bool = False


class Middleware(BaseModel):
    cors: CORS = CORS()
    https_redirect: HTTPSRedirect = HTTPSRedirect()
    trusted_host: TrustedHost = TrustedHost()
    gzip: GZip = GZip()


class FastAPIConfig(BaseModel):
    root_path: str = ""
    swagger: Swagger = Swagger()
    middleware: Middleware = Middleware()


class DatabaseConfig(BaseModel):
    """通用数据库配置（ORM 无关）。

    各 ORM 扩展从 loader.section("easy_fastapi.database", DatabaseConfig) 读取，
    自行转换为 ORM 特定连接 URL。
    """

    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=True)

    dialect: str = "mysql"  # mysql / postgres / sqlite
    username: str = "root"
    password: str = ""
    database: str = "easy_fastapi"
    host: str = "localhost"
    port: int | None = 3306  # 默认 3306（mysql）；设为 None 时不拼端口，让驱动用 dialect 默认值
    echo: bool = False
    timezone: str = "Asia/Shanghai"


class ResponseCodeConfig(BaseModel):
    """响应码配置——控制 JSON body code 与 HTTP status_code 的映射。

    style="http"：code = HTTP status（RESTful 约定，默认）
    style="zero_success"：成功 code=0，错误 code 仍用 HTTP status
    trace_id=True：错误响应（status_code >= 400）自动在 data 中附加 trace_id
    """

    style: Literal["http", "zero_success"] = "http"
    trace_id: bool = False


class EasyFastAPIConfig(_BaseModel):
    """easy_fastapi 核心配置段。

    extra='ignore'：扩展配置（auth/database/redis/static 等）在同一 YAML 段下，
    由各扩展按 loader.section("easy_fastapi.<name>") 独立加载校验；
    此模型仅消费框架自身核心字段，忽略扩展键。
    """

    model_config = ConfigDict(extra="ignore")

    response_code: ResponseCodeConfig = ResponseCodeConfig()
    upload_dir: str | None = None
