#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Optional, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from easy_pyoc import PathUtil

from .config import Config
from .exception.handlers import binding_exception_handler


class EasyFastAPI:

    def __init__(
            self,
            app: FastAPI,
            tortoise_config: Optional[dict] = None,
        ):
        self.app = app
        self.tortoise_config = tortoise_config

        self.config = Config()

        self.init_app(app)

    def init_app(self, app: FastAPI):
        if hasattr(app, 'easy_fastapi'):
            raise RuntimeError('一个 "EasyFastAPI" 实例已经注册到 FastAPI 应用中，请勿重复注册。')

        app.easy_fastapi = self
        app.root_path    = self.config.fastapi.root_path

        binding_exception_handler(app)

        # 绑定 http 中间件，强制返回 200 状态码
        if self.config.easy_fastapi.force_success_code:
            @app.middleware('http')
            async def response_status_code_middleware(request: Request, call_next: Callable[[Request], Response]) -> Response:
                response: Response = await call_next(request)

                response.status_code = 200

                return response

        # 添加 SPA 入口，挂载静态资源文件
        if self.config.easy_fastapi.spa.enabled:
            with PathUtil.open(self.config.easy_fastapi.spa.index_file, 'r', encoding='utf-8') as f:
                index_html = f.read()

                @app.get('/', tags=['单页应用'], summary='SPA 入口', response_class=HTMLResponse)
                async def spa():
                    return index_html

            app.mount(
                self.config.easy_fastapi.spa.static_url,
                StaticFiles(
                    directory=self.config.easy_fastapi.spa.static_dir,
                    html=True,
                ),
                'spa',
            )

        # 配置跨域中间件
        if self.config.fastapi.middleware.cors.enabled:
            app.add_middleware(
                CORSMiddleware,
                allow_origin_regex=self.config.fastapi.middleware.cors.allow_origin_regex,
                allow_origins=self.config.fastapi.middleware.cors.allow_origins,
                allow_methods=self.config.fastapi.middleware.cors.allow_methods,
                allow_headers=self.config.fastapi.middleware.cors.allow_headers,
                allow_credentials=self.config.fastapi.middleware.cors.allow_credentials,
                expose_headers=self.config.fastapi.middleware.cors.expose_headers,
                max_age=self.config.fastapi.middleware.cors.max_age,
            )

        if self.config.fastapi.middleware.https_redirect.enabled:
            app.add_middleware(HTTPSRedirectMiddleware)

        if self.config.fastapi.middleware.trusted_host.enabled:
            app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=self.config.fastapi.middleware.trusted_host.allowed_hosts,
            )

        if self.config.fastapi.middleware.gzip.enabled:
            app.add_middleware(
                GZipMiddleware,
                minimum_size=self.config.fastapi.middleware.gzip.minimum_size,
                compresslevel=self.config.fastapi.middleware.gzip.compress_level,
            )
