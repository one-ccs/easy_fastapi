from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def register_cors(app: FastAPI, config) -> None:
    """根据配置注册 CORS 中间件。"""
    if not config.enabled:
        return
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=config.allow_origin_regex,
        allow_origins=config.allow_origins,
        allow_methods=config.allow_methods,
        allow_headers=config.allow_headers,
        allow_credentials=config.allow_credentials,
        expose_headers=config.expose_headers,
        max_age=config.max_age,
    )
