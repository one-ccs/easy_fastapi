"""异常 handler 绑定测试。"""

import pytest
from easy_fastapi import (
    FailureException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from easy_fastapi.core.response_code import set_trace_id
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_trace_id():
    """每个测试前后重置 trace_id 开关。"""
    set_trace_id(False)
    yield
    set_trace_id(False)


def _create_test_app() -> FastAPI:
    """创建测试用 FastAPI 应用（装配 EasyFastAPI 框架）。"""
    app = FastAPI()

    @app.get("/raise/failure")
    async def raise_failure():
        raise FailureException("业务失败")

    @app.get("/raise/unauthorized")
    async def raise_unauthorized():
        raise UnauthorizedException()

    @app.get("/raise/forbidden")
    async def raise_forbidden():
        raise ForbiddenException()

    @app.get("/raise/notfound")
    async def raise_notfound():
        raise NotFoundException()

    @app.get("/raise/exception")
    async def raise_exception():
        raise Exception("服务器错误")

    return app


class TestExceptionHandlerBinding:
    def test_binding_exception_handler(self):
        """测试 binding_exception_handler 正确绑定。"""
        from easy_fastapi.core.handlers import binding_exception_handler

        app = FastAPI()
        binding_exception_handler(app)
        # 验证不抛异常即可
        assert app is not None

    def test_failure_exception_handler(self):
        app = _create_test_app()
        from easy_fastapi.core.handlers import binding_exception_handler

        binding_exception_handler(app)
        with TestClient(app) as client:
            response = client.get("/raise/failure")
            assert response.status_code == 400
            data = response.json()
            assert data["code"] == 400
            assert data["message"] == "业务失败"

    def test_unauthorized_exception_handler(self):
        app = _create_test_app()
        from easy_fastapi.core.handlers import binding_exception_handler

        binding_exception_handler(app)
        with TestClient(app) as client:
            response = client.get("/raise/unauthorized")
            assert response.status_code == 401
            data = response.json()
            assert data["code"] == 401

    def test_forbidden_exception_handler(self):
        app = _create_test_app()
        from easy_fastapi.core.handlers import binding_exception_handler

        binding_exception_handler(app)
        with TestClient(app) as client:
            response = client.get("/raise/forbidden")
            assert response.status_code == 403
            data = response.json()
            assert data["code"] == 403

    def test_not_found_exception_handler(self):
        app = _create_test_app()
        from easy_fastapi.core.handlers import binding_exception_handler

        binding_exception_handler(app)
        with TestClient(app) as client:
            response = client.get("/raise/notfound")
            assert response.status_code == 404
            data = response.json()
            assert data["code"] == 404

    def test_server_exception_handler(self):
        app = _create_test_app()
        from easy_fastapi.core.handlers import binding_exception_handler

        binding_exception_handler(app)
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/raise/exception")
            assert response.status_code == 500
            data = response.json()
            assert data["code"] == 500

    def test_server_exception_handler_with_trace_id(self):
        """trace_id 启用时，服务器异常响应含 id 字段。"""
        set_trace_id(True)
        app = _create_test_app()
        from easy_fastapi.core.handlers import binding_exception_handler

        binding_exception_handler(app)
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/raise/exception")
            assert response.status_code == 500
            data = response.json()
            assert data["code"] == 500
            assert "id" in data["data"]


class TestWWWAuthenticateHeader:
    """A5: 401 响应必须透传 WWW-Authenticate 头（RFC 7235）。"""

    def test_unauthorized_response_includes_www_authenticate_bearer(self):
        """UnauthorizedException 默认带 WWW-Authenticate: Bearer 头。"""
        app = _create_test_app()
        from easy_fastapi.core.handlers import binding_exception_handler

        binding_exception_handler(app)
        with TestClient(app) as client:
            response = client.get("/raise/unauthorized")
        assert response.status_code == 401
        assert response.headers.get("www-authenticate") == "Bearer"

    def test_custom_unauthorized_detail_preserved_with_www_authenticate(self):
        """自定义 detail 的 UnauthorizedException 也带 WWW-Authenticate 头。"""
        app = FastAPI()

        @app.get("/custom-unauthorized")
        async def custom_unauthorized():
            raise UnauthorizedException("自定义未认证消息")

        from easy_fastapi.core.handlers import binding_exception_handler

        binding_exception_handler(app)
        with TestClient(app) as client:
            response = client.get("/custom-unauthorized")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert response.headers["www-authenticate"] == "Bearer"
        assert response.json()["message"] == "自定义未认证消息"

    def test_unauthorized_exception_has_headers_attribute(self):
        """UnauthorizedException 类自带 headers = {"WWW-Authenticate": "Bearer"}。"""
        exc = UnauthorizedException()
        assert exc.headers is not None
        assert exc.headers.get("WWW-Authenticate") == "Bearer"

    def test_forbidden_response_does_not_include_www_authenticate(self):
        """403 响应不含 WWW-Authenticate 头。"""
        app = _create_test_app()
        from easy_fastapi.core.handlers import binding_exception_handler

        binding_exception_handler(app)
        with TestClient(app) as client:
            response = client.get("/raise/forbidden")
        assert response.status_code == 403
        assert "WWW-Authenticate" not in response.headers

    def test_http_401_via_starlette_includes_www_authenticate(self):
        """Starlette HTTPException(status_code=401) 也通过 http_exception_handler 透传头。"""
        from starlette.exceptions import HTTPException

        app = FastAPI()

        @app.get("/starlette-401")
        async def starlette_401():
            raise HTTPException(status_code=401, detail="nope", headers={"WWW-Authenticate": "Bearer"})

        from easy_fastapi.core.handlers import binding_exception_handler

        binding_exception_handler(app)
        with TestClient(app) as client:
            response = client.get("/starlette-401")
        assert response.status_code == 401
        assert response.headers.get("www-authenticate") == "Bearer"

    def test_http_401_without_headers_still_works(self):
        """Starlette HTTPException(status_code=401) 无 headers 时仍返回 401。"""
        from starlette.exceptions import HTTPException

        app = FastAPI()

        @app.get("/starlette-401-no-headers")
        async def starlette_401_no_headers():
            raise HTTPException(status_code=401, detail="nope")

        from easy_fastapi.core.handlers import binding_exception_handler

        binding_exception_handler(app)
        with TestClient(app) as client:
            response = client.get("/starlette-401-no-headers")
        assert response.status_code == 401

    def test_custom_unauthorized_with_custom_headers(self):
        """UnauthorizedException 传入自定义 headers 时透传。"""
        app = FastAPI()

        @app.get("/custom-headers-unauthorized")
        async def custom_headers_unauthorized():
            raise UnauthorizedException("custom", headers={"WWW-Authenticate": 'Bearer realm="app"'})

        from easy_fastapi.core.handlers import binding_exception_handler

        binding_exception_handler(app)
        with TestClient(app) as client:
            response = client.get("/custom-headers-unauthorized")
        assert response.status_code == 401
        assert "Bearer" in response.headers.get("www-authenticate", "")

    def test_failure_response_does_not_include_www_authenticate(self):
        """400 响应不含 WWW-Authenticate 头。"""
        app = _create_test_app()
        from easy_fastapi.core.handlers import binding_exception_handler

        binding_exception_handler(app)
        with TestClient(app) as client:
            response = client.get("/raise/failure")
        assert response.status_code == 400
        assert "WWW-Authenticate" not in response.headers


class TestValidationAndMethodNotAllowedHandlers:
    """E11: RequestValidationError → 400 参数校验错误 + 405 方法不允许。"""

    def test_request_validation_error_returns_400(self):
        """RequestValidationError（缺少 body）→ 400 参数有误。"""
        from easy_fastapi.core.handlers import binding_exception_handler
        from pydantic import BaseModel

        app = FastAPI()

        class Item(BaseModel):
            name: str
            price: float

        @app.post("/items")
        async def create_item(item: Item):
            return item

        binding_exception_handler(app)
        with TestClient(app, raise_server_exceptions=False) as client:
            # 不发 body → RequestValidationError
            response = client.post("/items")
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 400

    def test_request_validation_error_message_contains_bad_request(self):
        """RequestValidationError 默认消息来自 MSG_BAD_REQUEST。"""
        from easy_fastapi.core.handlers import binding_exception_handler
        from pydantic import BaseModel

        app = FastAPI()

        class Item(BaseModel):
            name: str

        @app.post("/items")
        async def create_item(item: Item):
            return item

        binding_exception_handler(app)
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/items")
        data = response.json()
        assert "Bad request" in data["message"]

    def test_method_not_allowed_returns_405(self):
        """不支持的 HTTP 方法 → 405。"""
        from easy_fastapi.core.handlers import binding_exception_handler

        app = FastAPI()

        @app.get("/get-only")
        async def get_only():
            return {"ok": True}

        binding_exception_handler(app)
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.delete("/get-only")
        assert response.status_code == 405

    def test_method_not_allowed_message(self):
        """405 响应体含 code=405 和消息。"""
        from easy_fastapi.core.handlers import binding_exception_handler

        app = FastAPI()

        @app.get("/get-only")
        async def get_only():
            return {"ok": True}

        binding_exception_handler(app)
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.delete("/get-only")
        data = response.json()
        assert data["code"] == 405
        assert data["message"]  # 消息非空

    def test_method_not_allowed_on_post_when_get_only(self):
        """GET-only 路由用 POST 请求 → 405。"""
        from easy_fastapi.core.handlers import binding_exception_handler

        app = FastAPI()

        @app.get("/get-only")
        async def get_only():
            return {"ok": True}

        binding_exception_handler(app)
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/get-only")
        assert response.status_code == 405

    def test_validation_error_with_wrong_type_returns_400(self):
        """字段类型错误 → RequestValidationError → 400。"""
        from easy_fastapi.core.handlers import binding_exception_handler
        from pydantic import BaseModel

        app = FastAPI()

        class Item(BaseModel):
            count: int

        @app.post("/items")
        async def create_item(item: Item):
            return item

        binding_exception_handler(app)
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/items", json={"count": "not_a_number"})
        assert response.status_code == 400

    def test_get_method_works_on_get_route(self):
        """GET 路由正常 GET 请求 → 200（对照：405 测试的前提）。"""
        from easy_fastapi.core.handlers import binding_exception_handler

        app = FastAPI()

        @app.get("/get-only")
        async def get_only():
            return {"ok": True}

        binding_exception_handler(app)
        with TestClient(app) as client:
            response = client.get("/get-only")
        assert response.status_code == 200

    def test_valid_body_passes_validation(self):
        """正确 body → 200（对照：400 测试的前提）。"""
        from easy_fastapi.core.handlers import binding_exception_handler
        from pydantic import BaseModel

        app = FastAPI()

        class Item(BaseModel):
            name: str

        @app.post("/items")
        async def create_item(item: Item):
            return item

        binding_exception_handler(app)
        with TestClient(app) as client:
            response = client.post("/items", json={"name": "test"})
        assert response.status_code == 200
