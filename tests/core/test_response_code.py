"""响应码策略测试（ResponseCodeStrategy / set_strategy / get_strategy）。"""

import pytest
from easy_fastapi.core.response_code import (
    ResponseCodeStrategy,
    ZeroSuccessStrategy,
    get_strategy,
    set_strategy,
    set_trace_id,
)


@pytest.fixture(autouse=True)
def _reset_strategy():
    """每个测试前后重置为默认 http 策略和 trace_id 关闭。"""
    set_strategy("http")
    set_trace_id(False)
    yield
    set_strategy("http")
    set_trace_id(False)


# ── ResponseCodeStrategy（默认 http 策略）──


class TestResponseCodeStrategy:
    def test_success_code_returns_status(self):
        s = ResponseCodeStrategy()
        assert s.success_code(200) == 200
        assert s.success_code(201) == 201

    def test_error_code_returns_status(self):
        s = ResponseCodeStrategy()
        assert s.error_code(400) == 400
        assert s.error_code(401) == 401

    def test_http_status_for_valid_code(self):
        s = ResponseCodeStrategy()
        assert s.http_status_for(200) == 200
        assert s.http_status_for(404) == 404

    def test_http_status_for_invalid_code_falls_back(self):
        s = ResponseCodeStrategy()
        assert s.http_status_for(0) == 200
        assert s.http_status_for(999) == 200
        assert s.http_status_for(40001) == 200


# ── ZeroSuccessStrategy ──


class TestZeroSuccessStrategy:
    def test_success_code_returns_zero(self):
        s = ZeroSuccessStrategy()
        assert s.success_code(200) == 0
        assert s.success_code(201) == 0

    def test_error_code_returns_status(self):
        s = ZeroSuccessStrategy()
        assert s.error_code(400) == 400
        assert s.error_code(401) == 401

    def test_http_status_for_zero(self):
        s = ZeroSuccessStrategy()
        assert s.http_status_for(0) == 200  # code=0 → HTTP 200

    def test_http_status_for_nonzero(self):
        s = ZeroSuccessStrategy()
        assert s.http_status_for(400) == 400  # code=400 → HTTP 400
        assert s.http_status_for(40001) == 40001  # 自定义业务码 → 直接用


# ── set_strategy / get_strategy ──


class TestStrategySwitching:
    def test_default_is_http(self):
        assert isinstance(get_strategy(), ResponseCodeStrategy)

    def test_set_zero_success(self):
        set_strategy("zero_success")
        assert isinstance(get_strategy(), ZeroSuccessStrategy)

    def test_set_http_resets(self):
        set_strategy("zero_success")
        set_strategy("http")
        assert isinstance(get_strategy(), ResponseCodeStrategy)

    def test_strategy_affects_result(self):
        from easy_fastapi.core.result import Result

        d = Result("成功")
        assert d.code == 200

        set_strategy("zero_success")
        d = Result("成功")
        assert d.code == 0

    def test_strategy_affects_response_result(self):
        from easy_fastapi.core.result import ResponseResult

        r = ResponseResult("成功")
        assert r.status_code == 200
        body = r.body.decode()
        assert '"code":200' in body

        set_strategy("zero_success")
        r = ResponseResult("成功")
        assert r.status_code == 200
        body = r.body.decode()
        assert '"code":0' in body

    def test_error_codes_unchanged_in_zero_success(self):
        """zero_success 模式下错误 code 仍用 HTTP status。"""
        from easy_fastapi.core.result import ResponseResult

        set_strategy("zero_success")
        r = ResponseResult.failure("错误")
        assert r.status_code == 400
        body = r.body.decode()
        assert '"code":400' in body

        r = ResponseResult.unauthorized("未授权")
        assert r.status_code == 401
        body = r.body.decode()
        assert '"code":401' in body


# ── ResponseResult code/status_code 分离 ──


class TestCodeStatusSeparation:
    def test_explicit_code_and_status(self):
        """显式设置 code 和 status_code——body code 与 HTTP status 独立。"""
        from easy_fastapi.core.result import ResponseResult

        r = ResponseResult("自定义错误", code=40001, status_code=400)
        assert r.status_code == 400
        body = r.body.decode()
        assert '"code":40001' in body

    def test_only_status_code_infers_body_code(self):
        """只传 status_code → body code 由策略推算。"""
        from easy_fastapi.core.result import ResponseResult

        r = ResponseResult("成功", status_code=200)
        assert r.status_code == 200
        assert '"code":200' in r.body.decode()

        set_strategy("zero_success")
        r = ResponseResult("成功", status_code=200)
        assert r.status_code == 200
        assert '"code":0' in r.body.decode()

    def test_only_code_infers_status(self):
        """只传 code → HTTP status 由策略推算。"""
        from easy_fastapi.core.result import ResponseResult

        r = ResponseResult("成功", code=0)
        assert r.status_code == 200  # code=0 → http_status_for(0) = 200
        assert '"code":0' in r.body.decode()

    def test_failure_exception_custom_code(self):
        """FailureException 支持 code 字段——自定义业务码与 HTTP status 分离。"""
        from easy_fastapi.core.exceptions import FailureException

        exc = FailureException("参数错误", status_code=400, code=40001)
        assert exc.status_code == 400
        assert exc.code == 40001

    def test_failure_exception_default_code_is_none(self):
        """不传 code 时 FailureException.code 为 None。"""
        from easy_fastapi.core.exceptions import FailureException

        exc = FailureException("错误")
        assert exc.code is None


# ── Result code 分离 ──


class TestResultCodeSeparation:
    def test_explicit_code(self):
        from easy_fastapi.core.result import Result

        d = Result("成功", code=0)
        assert d.code == 0

    def test_failure_explicit_code(self):
        from easy_fastapi.core.result import Result

        d = Result.failure("错误", code=40001)
        assert d.code == 40001

    def test_default_code_follows_strategy(self):
        from easy_fastapi.core.result import Result

        d = Result("成功")
        assert d.code == 200

        set_strategy("zero_success")
        d = Result("成功")
        assert d.code == 0
