# easy_fastapi

Easy FastAPI 运行时库：扩展化 FastAPI 框架 + ORM/auth/redis/migration 扩展。

## 安装

```bash
uv add easy_fastapi
```

## 使用

```python
from fastapi import FastAPI
from easy_fastapi import EasyFastAPI

app = FastAPI()
efa = EasyFastAPI(app, config_path="easy-fastapi.yaml")
efa.use(...)
```
