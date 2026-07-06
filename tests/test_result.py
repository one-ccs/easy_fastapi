"""统一响应模型测试。"""

import pytest
from easy_fastapi import BaseResult, ResponseResult, Result
from easy_fastapi.core.response_code import is_trace_id_enabled, set_trace_id
from fastapi.responses import JSONResponse


@pytest.fixture(autouse=True)
def _reset_trace_id():
    """每个测试前后重置 trace_id 开关。"""
    set_trace_id(False)
    yield
    set_trace_id(False)


class TestBaseResult:
    def test_base_result_basic(self):
        r = BaseResult[int](code=200, message="ok", data=42)
        assert r.code == 200
        assert r.message == "ok"
        assert r.data == 42

    def test_base_result_none_data(self):
        r = BaseResult[str](code=404, message="not found")
        assert r.data is None

    def test_base_result_generic(self):
        r = BaseResult[list](code=200, message="ok", data=[1, 2, 3])
        assert r.data == [1, 2, 3]


class TestResult:
    def test_result_returns_base_result(self):
        r = Result()
        assert isinstance(r, BaseResult)

    def test_result_default(self):
        r = Result()
        assert r.code == 200
        assert r.message == "Request succeeded"
        assert r.data is None

    def test_result_with_data(self):
        r = Result("成功", data={"id": 1})
        assert r.code == 200
        assert r.message == "成功"
        assert r.data == {"id": 1}

    def test_result_failure(self):
        r = Result.failure("失败")
        assert isinstance(r, BaseResult)
        assert r.code == 400
        assert r.message == "失败"
        assert r.data is None

    def test_result_failure_with_data(self):
        r = Result.failure("失败", data={"reason": "test"})
        assert isinstance(r, BaseResult)
        assert r.code == 400
        assert r.data == {"reason": "test"}


class TestResponseResult:
    def test_response_result_default(self):
        r = ResponseResult()
        assert isinstance(r, JSONResponse)
        assert r.status_code == 200
        body = __import__("json").loads(r.body)
        assert body["message"] == "Request succeeded"

    def test_response_result_with_data(self):
        r = ResponseResult("成功", data={"id": 1})
        assert isinstance(r, JSONResponse)
        assert r.status_code == 200

    def test_response_result_failure(self):
        r = ResponseResult.failure("失败")
        assert isinstance(r, JSONResponse)
        assert r.status_code == 400

    def test_response_result_unauthorized(self):
        r = ResponseResult.unauthorized()
        assert isinstance(r, JSONResponse)
        assert r.status_code == 401

    def test_response_result_forbidden(self):
        r = ResponseResult.forbidden()
        assert isinstance(r, JSONResponse)
        assert r.status_code == 403

    def test_response_result_not_found(self):
        r = ResponseResult.not_found()
        assert isinstance(r, JSONResponse)
        assert r.status_code == 404


class TestResolveCodes:
    """ResponseResult._resolve_codes 推算逻辑。"""

    def test_both_explicit(self):
        code, status = ResponseResult._resolve_codes(code=40001, status_code=400)
        assert code == 40001
        assert status == 400

    def test_only_code_infers_status(self):
        code, status = ResponseResult._resolve_codes(code=200)
        assert code == 200
        assert status == 200

    def test_only_status_code_success(self):
        code, status = ResponseResult._resolve_codes(status_code=200)
        assert code == 200
        assert status == 200

    def test_only_status_code_error(self):
        code, status = ResponseResult._resolve_codes(status_code=400)
        assert code == 400
        assert status == 400

    def test_neither_defaults_to_success(self):
        code, status = ResponseResult._resolve_codes()
        assert code == 200
        assert status == 200

    def test_only_code_zero_success_strategy(self):
        from easy_fastapi.core.response_code import set_strategy

        set_strategy("zero_success")
        code, status = ResponseResult._resolve_codes(code=0)
        assert code == 0
        assert status == 200
        set_strategy("http")

    def test_only_status_code_zero_success_strategy(self):
        from easy_fastapi.core.response_code import set_strategy

        set_strategy("zero_success")
        code, status = ResponseResult._resolve_codes(status_code=200)
        assert code == 0
        assert status == 200
        set_strategy("http")


class TestTraceId:
    """trace_id 配置化：错误响应自动附加 trace_id。"""

    def test_trace_id_disabled_no_id_in_error(self):
        """trace_id 关闭时，错误响应不含 id 字段。"""
        set_trace_id(False)
        r = ResponseResult.failure("错误")
        import json

        body = json.loads(r.body)
        # data 为 null 或 dict，均不应含 id
        data = body.get("data")
        if isinstance(data, dict):
            assert "id" not in data

    def test_trace_id_enabled_adds_id_to_error(self):
        """trace_id 开启时，错误响应自动附加 id 字段。"""
        set_trace_id(True)
        r = ResponseResult.failure("错误")
        import json

        body = json.loads(r.body)
        assert "id" in body["data"]
        assert len(body["data"]["id"]) == 32  # hex uuid

    def test_trace_id_not_added_to_success(self):
        """trace_id 开启时，成功响应不含 id 字段。"""
        set_trace_id(True)
        r = ResponseResult("成功", data={"key": "val"})
        import json

        body = json.loads(r.body)
        assert "id" not in body["data"]

    def test_trace_id_merges_with_dict_data(self):
        """trace_id 开启时，dict data 中合并 id 字段。"""
        set_trace_id(True)
        r = ResponseResult.failure("错误", data={"reason": "test"})
        import json

        body = json.loads(r.body)
        assert body["data"]["reason"] == "test"
        assert "id" in body["data"]
        assert len(body["data"]["id"]) == 32

    def test_trace_id_replaces_non_dict_data(self):
        """trace_id 开启时，非 dict data（如 None）用 {"id": ...} 替代。"""
        set_trace_id(True)
        r = ResponseResult.failure("错误")
        import json

        body = json.loads(r.body)
        assert body["data"] == {"id": body["data"]["id"]}  # 只含 id

    def test_trace_id_unique_per_response(self):
        """每次错误响应生成不同 trace_id。"""
        set_trace_id(True)
        r1 = ResponseResult.failure("err1")
        r2 = ResponseResult.failure("err2")
        import json

        id1 = json.loads(r1.body)["data"]["id"]
        id2 = json.loads(r2.body)["data"]["id"]
        assert id1 != id2

    def test_trace_id_enabled_all_error_types(self):
        """trace_id 开启时，所有错误响应类型都带 id。"""
        set_trace_id(True)
        import json

        for method in [ResponseResult.unauthorized, ResponseResult.forbidden, ResponseResult.not_found]:
            r = method()
            body = json.loads(r.body)
            assert "id" in body["data"], f"{method.__name__} 缺少 trace_id"

    def test_trace_id_disabled_default(self):
        """默认 trace_id 关闭。"""
        assert is_trace_id_enabled() is False


class TestExcLogging:
    """exc 参数：传入时自动记录 error 日志。"""

    def test_exc_logs_error(self):
        """传了 exc 时记录 error 日志。"""
        import logging
        from unittest.mock import patch

        set_trace_id(True)
        with patch.object(logging.getLogger("easy_fastapi"), "error") as mock_log:
            ResponseResult("服务器错误", status_code=500, exc=RuntimeError("boom"))
            mock_log.assert_called_once()

    def test_exc_logs_with_trace_id(self):
        """trace_id 开启 + 传 exc → 日志含 trace_id，响应也含 id。"""
        set_trace_id(True)
        import json

        r = ResponseResult("服务器错误", status_code=500, exc=RuntimeError("boom"))
        body = json.loads(r.body)
        assert "id" in body["data"]

    def test_exc_logs_without_trace_id(self):
        """trace_id 关闭 + 传 exc → 日志仍记录（trace_id 位显示 -）。"""
        set_trace_id(False)
        import logging
        from unittest.mock import patch

        with patch.object(logging.getLogger("easy_fastapi"), "error") as mock_log:
            ResponseResult("服务器错误", status_code=500, exc=RuntimeError("boom"))
            mock_log.assert_called_once()
            # 第一个位置参数格式："异常请求[%s] - %s - %s"
            call_args = mock_log.call_args[0]
            assert call_args[1] == "-"  # trace_id 为 None → 显示 "-"

    def test_no_exc_no_log(self):
        """不传 exc 时不记录日志。"""
        import logging
        from unittest.mock import patch

        with patch.object(logging.getLogger("easy_fastapi"), "error") as mock_log:
            ResponseResult.failure("普通错误")
            mock_log.assert_not_called()

    def test_exc_info_in_log(self):
        """日志应包含 exc_info。"""
        import logging
        from unittest.mock import patch

        with patch.object(logging.getLogger("easy_fastapi"), "error") as mock_log:
            ResponseResult("错误", status_code=500, exc=RuntimeError("boom"))
            kwargs = mock_log.call_args[1]
            assert "exc_info" in kwargs
