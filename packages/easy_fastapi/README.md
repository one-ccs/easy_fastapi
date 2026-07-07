<p align="center">
  <img src="../../docs/assets/title.svg" alt="Easy FastAPI" width="520">
</p>
<h3 align="center">Runtime Framework</h3>
<p align="center">
  <a href="https://github.com/one-ccs/easy_fastapi/actions/workflows/ci.yaml">
    <img src="https://github.com/one-ccs/easy_fastapi/actions/workflows/ci.yaml/badge.svg" alt="CI">
  </a>
  <a href="https://pypi.org/project/easy-fastapi">
    <img src="https://img.shields.io/pypi/v/easy-fastapi?color=%2334D058&label=PyPI" alt="PyPI">
  </a>
  <a href="https://pypi.org/project/easy-fastapi">
    <img src="https://img.shields.io/pypi/pyversions/easy-fastapi.svg?color=%2334D058" alt="Python">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT">
  </a>
</p>

> Extensible FastAPI framework with pluggable ORM, auth, Redis, i18n and static extensions.

<img src="../../docs/assets/demo.gif" alt="Demo" style="max-width: 1024px; width: 100%; height: auto;">

## 📦 Install

```bash
uv add easy_fastapi
```

## 🚀 Usage

```python
from fastapi import FastAPI
from easy_fastapi import EasyFastAPI

app = FastAPI()
efa = EasyFastAPI(app, config_path="easy-fastapi.yaml")

# Chain extensions — pick what you need
efa.use(TortoiseExtension()).use(AuthExtension()).use(RedisExtension())
```

## 🧩 Extensions

| Extension | Description |
|-----------|-------------|
| 🐢 `orm.tortoise` | Tortoise ORM data layer |
| 🐍 `orm.sqlalchemy` | SQLAlchemy ORM data layer |
| 📦 `orm.sqlmodel` | SQLModel ORM data layer |
| 🔐 `auth` | JWT + argon2 auth, zero ORM coupling |
| ⚡ `redis` | Redis persistence, falls back to memory |
| 🌍 `i18n` | Internationalization (gettext + contextvars) |
| 📁 `static` | Static file serving |
