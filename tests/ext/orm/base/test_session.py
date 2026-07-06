"""共享 session 工厂测试。"""

import inspect


def test_make_session_factory_signature():
    """make_session_factory 应接受 async_session_class 参数。"""
    from easy_fastapi.ext.orm.base.session import make_session_factory

    sig = inspect.signature(make_session_factory)
    params = list(sig.parameters.keys())
    assert "db_url" in params
    assert "async_session_class" in params


def test_make_db_session_factory_signature():
    """make_db_session_factory 应接受 async_session_class 参数。"""
    from easy_fastapi.ext.orm.base.session import make_db_session_factory

    sig = inspect.signature(make_db_session_factory)
    params = list(sig.parameters.keys())
    assert "db_url" in params
    assert "async_session_class" in params
