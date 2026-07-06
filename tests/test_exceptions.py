"""业务异常体系测试。"""

import pytest
from easy_fastapi import (
    EasyFastAPIError,
    FailureException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from easy_fastapi.core.exceptions import (
    MSG_BAD_REQUEST,
    MSG_FAILURE,
    MSG_FORBIDDEN,
    MSG_METHOD_NOT_ALLOWED,
    MSG_NOT_FOUND,
    MSG_UNAUTHORIZED,
)
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def _reset_i18n():
    """每个测试前后重置 i18n 状态（避免 locale 泄漏）。"""
    from easy_fastapi.core.i18n import _current_locale, _current_translator

    _current_locale.set(None)
    _current_translator.set(lambda message: message)
    yield
    _current_locale.set(None)
    _current_translator.set(lambda message: message)


class TestFrameworkExceptions:
    def test_extension_error_is_easy_fastapi_error(self):
        from easy_fastapi import ExtensionError

        assert issubclass(ExtensionError, EasyFastAPIError)

    def test_config_error_is_easy_fastapi_error(self):
        from easy_fastapi import ConfigError

        assert issubclass(ConfigError, EasyFastAPIError)


class TestBusinessExceptions:
    def test_failure_exception_is_http_exception(self):
        assert issubclass(FailureException, HTTPException)

    def test_failure_exception_default(self):
        exc = FailureException()
        assert exc.status_code == 400
        assert exc.detail == "Request failed"

    def test_failure_exception_custom_detail(self):
        exc = FailureException("自定义错误")
        assert exc.detail == "自定义错误"
        assert exc.status_code == 400

    def test_unauthorized_exception(self):
        exc = UnauthorizedException()
        assert exc.status_code == 401
        assert exc.detail == "Please login first"
        assert exc.headers == {"WWW-Authenticate": "Bearer"}

    def test_forbidden_exception(self):
        exc = ForbiddenException()
        assert exc.status_code == 403
        assert exc.detail == "Permission denied"

    def test_not_found_exception(self):
        exc = NotFoundException()
        assert exc.status_code == 404
        assert exc.detail == "Resource not found"

    def test_unauthorized_is_subclass_of_failure(self):
        assert issubclass(UnauthorizedException, FailureException)

    def test_forbidden_is_subclass_of_failure(self):
        assert issubclass(ForbiddenException, FailureException)

    def test_not_found_is_subclass_of_failure(self):
        assert issubclass(NotFoundException, FailureException)

    def test_raise_failure_exception(self):
        with pytest.raises(FailureException) as exc_info:
            raise FailureException("测试异常")
        assert str(exc_info.value.detail) == "测试异常"


class TestMessageConstantsSingleSource:
    """E4: 统一消息常量 — 验证 exceptions/result/handlers 共用单一来源。"""

    def test_msg_constants_exist(self):
        """所有消息常量均可在 core.exceptions 中导入。"""
        assert MSG_FAILURE == "Request failed"
        assert MSG_UNAUTHORIZED == "Please login first"
        assert MSG_FORBIDDEN == "Permission denied"
        assert MSG_NOT_FOUND == "Resource not found"
        assert MSG_METHOD_NOT_ALLOWED == "Method not allowed"
        assert MSG_BAD_REQUEST == "Bad request"

    def test_failure_exception_detail_matches_constant(self):
        """FailureException.detail 来自 MSG_FAILURE 常量。"""
        assert FailureException.detail == MSG_FAILURE

    def test_unauthorized_exception_detail_matches_constant(self):
        """UnauthorizedException.detail 来自 MSG_UNAUTHORIZED 常量。"""
        assert UnauthorizedException.detail == MSG_UNAUTHORIZED

    def test_forbidden_exception_detail_matches_constant(self):
        """ForbiddenException.detail 来自 MSG_FORBIDDEN 常量。"""
        assert ForbiddenException.detail == MSG_FORBIDDEN

    def test_not_found_exception_detail_matches_constant(self):
        """NotFoundException.detail 来自 MSG_NOT_FOUND 常量。"""
        assert NotFoundException.detail == MSG_NOT_FOUND

    def test_result_failure_uses_constant(self):
        """Result.failure() 默认消息来自 MSG_FAILURE 常量。"""
        from easy_fastapi.core.result import Result

        result = Result.failure()
        assert result.message == MSG_FAILURE

    def test_response_result_unauthorized_uses_constant(self):
        """ResponseResult.unauthorized() 默认消息来自 MSG_UNAUTHORIZED 常量。"""
        from easy_fastapi.core.result import ResponseResult

        resp = ResponseResult.unauthorized()
        body = resp.body.decode()
        assert MSG_UNAUTHORIZED in body

    def test_response_result_forbidden_uses_constant(self):
        """ResponseResult.forbidden() 默认消息来自 MSG_FORBIDDEN 常量。"""
        from easy_fastapi.core.result import ResponseResult

        resp = ResponseResult.forbidden()
        body = resp.body.decode()
        assert MSG_FORBIDDEN in body

    def test_response_result_not_found_uses_constant(self):
        """ResponseResult.not_found() 默认消息来自 MSG_NOT_FOUND 常量。"""
        from easy_fastapi.core.result import ResponseResult

        resp = ResponseResult.not_found()
        body = resp.body.decode()
        assert MSG_NOT_FOUND in body

    def test_response_result_method_not_allowed_uses_constant(self):
        """ResponseResult.method_not_allowed() 默认消息来自 MSG_METHOD_NOT_ALLOWED 常量。"""
        from easy_fastapi.core.result import ResponseResult

        resp = ResponseResult.method_not_allowed()
        body = resp.body.decode()
        assert MSG_METHOD_NOT_ALLOWED in body
