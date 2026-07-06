from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware


def register_gzip(app: FastAPI, config) -> None:
    """根据配置注册 GZip 压缩中间件。"""
    if not config.enabled:
        return
    app.add_middleware(
        GZipMiddleware,
        minimum_size=config.minimum_size,
        compresslevel=config.compress_level,
    )
