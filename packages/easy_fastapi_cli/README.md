<p align="center">
  <img src="../../docs/assets/title.svg" alt="Easy FastAPI" width="520">
</p>
<h3 align="center">Scaffold CLI</h3>
<p align="center">
  <a href="https://github.com/one-ccs/easy_fastapi/actions/workflows/ci.yaml">
    <img src="https://github.com/one-ccs/easy_fastapi/actions/workflows/ci.yaml/badge.svg" alt="CI">
  </a>
  <a href="https://pypi.org/project/easy-fastapi-cli">
    <img src="https://img.shields.io/pypi/v/easy-fastapi-cli?color=%2334D058&label=PyPI" alt="PyPI">
  </a>
  <a href="https://pypi.org/project/easy-fastapi-cli">
    <img src="https://img.shields.io/pypi/pyversions/easy-fastapi-cli.svg?color=%2334D058" alt="Python">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT">
  </a>
</p>

> CLI to scaffold FastAPI projects — pick your ORM, auth, Redis, frontend in one command.

<img src="../../docs/assets/demo.gif" alt="Demo" style="max-width: 1024px; width: 100%; height: auto;">

## 📦 Install

```bash
uv tool install easy-fastapi-cli
```

## ⌨️ Commands

| Command | Description |
|---------|-------------|
| `efa create myapp` | Interactive project creation |
| `efa run --reload` | Start dev server |
| `efa db init` | Initialize migration config |
| `efa db migrate` | Generate migration files |
| `efa db upgrade` | Apply migrations |
| `efa db sync` | Create tables directly (dev) |
| `efa gen` | Generate CRUD code from models |

## 🚀 Quick Example

```bash
# Backend + SQLAlchemy + PostgreSQL + auth + Redis
efa create myapp --no-interactive \
  --project-name myapp --package-name myapp \
  --database --orm sqlalchemy --db-dialect postgres \
  --auth --redis
```
