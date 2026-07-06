"""核心固定配置模型（fastapi 段）测试。

覆盖：各模型默认值、嵌套结构、extra='forbid' 严格模式、字段可覆盖、
模型类型隔离（默认实例不共享可变状态）、完整 FastAPIConfig 组装。
"""

import pytest
from easy_fastapi.core.config.models import (
    CORS,
    Contact,
    FastAPIConfig,
    GZip,
    HTTPSRedirect,
    License,
    Middleware,
    Swagger,
    TrustedHost,
)
from pydantic import ValidationError

# ---- 默认值（正常路径） ----


def test_contact_defaults():
    c = Contact()
    assert c.name == "one-ccs"
    assert c.email == "one-ccs@foxmail.com"
    assert c.url is None


def test_license_defaults():
    lic = License()
    assert lic.name == ""
    assert lic.url is None


def test_swagger_defaults():
    s = Swagger()
    assert s.title == "Easy FastAPI"
    assert s.version == "0.1.0"
    assert s.docs_url == "/docs"
    assert s.openapi_url == "/openapi.json"
    assert isinstance(s.contact, Contact)
    assert isinstance(s.license, License)


def test_cors_defaults():
    c = CORS()
    assert c.enabled is False
    assert c.allow_origins == ["*"]
    assert c.allow_credentials is True
    assert c.max_age == 600


def test_middleware_defaults():
    m = Middleware()
    assert m.cors.enabled is False
    assert m.https_redirect.enabled is False
    assert m.trusted_host.enabled is False
    assert m.gzip.enabled is False
    assert isinstance(m.cors, CORS)
    assert isinstance(m.https_redirect, HTTPSRedirect)
    assert isinstance(m.trusted_host, TrustedHost)
    assert isinstance(m.gzip, GZip)


def test_fastapi_config_defaults():
    f = FastAPIConfig()
    assert f.root_path == ""
    assert isinstance(f.swagger, Swagger)
    assert isinstance(f.middleware, Middleware)


# ---- extra='forbid' 严格模式（错误路径） ----


def test_swagger_forbid_extra_field():
    with pytest.raises(ValidationError):
        Swagger(typo_field=1)


def test_contact_forbid_extra_field():
    with pytest.raises(ValidationError):
        Contact(phone="123")


def test_cors_forbid_extra_field():
    with pytest.raises(ValidationError):
        CORS(unknown_option=True)


def test_fastapi_config_forbid_extra_field():
    with pytest.raises(ValidationError):
        FastAPIConfig(unknown_top=1)


# ---- 字段可覆盖（正常路径） ----


def test_swagger_fields_overridable():
    s = Swagger(title="My API", version="2.0.0", docs_url="/api/docs")
    assert s.title == "My API"
    assert s.version == "2.0.0"
    assert s.docs_url == "/api/docs"


def test_cors_enable_and_origins_overridable():
    c = CORS(enabled=True, allow_origins=["https://a.com", "https://b.com"], max_age=120)
    assert c.enabled is True
    assert c.allow_origins == ["https://a.com", "https://b.com"]
    assert c.max_age == 120


def test_gzip_defaults_and_override():
    assert GZip().compress_level == 5
    assert GZip().minimum_size == 1000
    g = GZip(enabled=True, compress_level=9)
    assert g.enabled is True
    assert g.compress_level == 9


# ---- 嵌套覆盖与类型隔离 ----


def test_swagger_nested_contact_override():
    s = Swagger(contact=Contact(name="alice", email="alice@x.com", url="https://x.com"))
    assert s.contact.name == "alice"
    assert s.contact.email == "alice@x.com"
    assert s.contact.url == "https://x.com"


def test_default_instances_are_independent():
    # 两个 Swagger 默认实例的 contact 不应是同一对象（避免共享可变默认值）
    a, b = Swagger(), Swagger()
    assert a.contact is not b.contact
    a.contact.name = "mutated"
    assert b.contact.name == "one-ccs"


# ---- EasyFastAPIConfig（剥离 SPA/authentication 到 ext） ----

from easy_fastapi.core.config.models import EasyFastAPIConfig  # noqa: E402


def test_easy_fastapi_config_defaults():
    e = EasyFastAPIConfig()
    assert e.response_code.style == "http"
    assert e.upload_dir is None


def test_easy_fastapi_config_ignores_extension_fields():
    # 扩展配置键（auth/database 等）在 easy_fastapi 段下，核心模型忽略而非拒绝
    e = EasyFastAPIConfig(authentication={"secret_key": "x"}, database={"url": "sqlite:///x.db"})
    assert e.response_code.style == "http"  # 核心字段正常
    assert not hasattr(e, "authentication")  # 扩展键被忽略
    assert not hasattr(e, "database")


def test_easy_fastapi_config_fields_overridable():
    e = EasyFastAPIConfig(response_code={"style": "zero_success"}, upload_dir="/var/uploads")
    assert e.response_code.style == "zero_success"
    assert e.upload_dir == "/var/uploads"


def test_easy_fastapi_config_is_pydantic_base_model_subclass():
    # EasyFastAPIConfig 继承自 pydantic BaseModel（用 extra='ignore' 容纳扩展键）
    from pydantic import BaseModel as PydanticBaseModel

    assert issubclass(EasyFastAPIConfig, PydanticBaseModel)


def test_easy_fastapi_config_no_authentication_attribute():
    # authentication 段不在核心配置中
    e = EasyFastAPIConfig()
    assert not hasattr(e, "authentication")
