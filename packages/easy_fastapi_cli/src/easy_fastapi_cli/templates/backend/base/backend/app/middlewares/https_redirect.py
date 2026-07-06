from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware


def register_https_redirect(app: FastAPI, config) -> None:
    """根据配置注册 HTTPS 重定向中间件。"""
    if not config.enabled:
        return
    app.add_middleware(HTTPSRedirectMiddleware)
