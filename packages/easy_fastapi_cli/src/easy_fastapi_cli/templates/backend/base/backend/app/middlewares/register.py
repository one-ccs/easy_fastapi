from fastapi import FastAPI

from .cors import register_cors
from .gzip import register_gzip
from .https_redirect import register_https_redirect
from .trusted_host import register_trusted_host


def register_middlewares(app: FastAPI) -> None:
    """根据配置注册中间件。

    中间件执行顺序为洋葱模型：最后注册的最先执行。
    当前顺序：GZip → TrustedHost → HTTPSRedirect → CORS
    （CORS 最内层，确保跨域预检请求正确处理）
    """
    efa = app.state.easy_fastapi
    mw = efa.fastapi_config.middleware

    register_cors(app, mw.cors)
    register_https_redirect(app, mw.https_redirect)
    register_trusted_host(app, mw.trusted_host)
    register_gzip(app, mw.gzip)
