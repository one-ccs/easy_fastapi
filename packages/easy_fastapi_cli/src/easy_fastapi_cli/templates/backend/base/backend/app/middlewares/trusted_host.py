from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware


def register_trusted_host(app: FastAPI, config) -> None:
    """根据配置注册信任主机中间件。"""
    if not config.enabled:
        return
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=config.allowed_hosts,
    )
