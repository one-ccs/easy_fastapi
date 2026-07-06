<p align="center">
  <img src="docs/assets/title.svg" alt="Easy FastAPI" width="520">
</p>
<h3 align="center">FastAPI Fullstack Scaffold</h3>

<p align="center">
  <em>Generate a full-stack FastAPI project with a single command: 3 ORMs × auth × Redis × frontend SDK</em>
</p>
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

<img src="docs/assets/demo.gif" alt="Demo" style="max-width: 1024px; width: 100%; height: auto;">

## ✨ Features

- **Dual-mode directory**: `backend-only` (API only) or `fullstack` (`backend/` + `frontend/` monorepo)
- **3 ORM choices**: Tortoise ORM / SQLAlchemy / SQLModel, unified `DbSession` / `UserModelProtocol` / `ModelIntrospector` protocols
- **Cross-ORM auth**: pwdlib (argon2 default) + PyJWT, zero ORM coupling
- **Redis extension**: override persistence, `enabled=false` falls back to memory
- **Frontend skeleton**: pnpm workspace monorepo, @hey-api/openapi-ts SDK generation, user creates apps in `frontend/apps/`
- **4 CLI commands + plugin extensions**: `efa create` / `efa run` / `efa db {init,migrate,upgrade,sync}` / `efa gen` + `efa i18n {init,compile,update}` (via CLIPlugin)
- **Optional dependency guards**: missing packages auto-hint `uv add <pkg>`
- **Strict config**: `easy-fastapi.yaml` + `ConfigLoader`, `extra='forbid'`, env overlay

## 🚀 Quick Start

### Installation

```bash
# Recommended: uv (CLI includes runtime)
uv tool install easy-fastapi-cli

# Or run temporarily
uvx efa --help
```

### 30-Second Experience

```bash
efa create myapp       # Interactive project creation
cd myapp
uv sync
efa run --reload       # Start dev server
```

Visit `http://localhost:8000/docs` for Swagger UI.

<details>
<summary>Non-interactive / Full Options</summary>

```bash
# Backend + Tortoise + MySQL + auth
efa create myapp --no-interactive \
  --project-name myapp --package-name myapp \
  --database --orm tortoise --db-dialect mysql --auth

# Full-stack + SQLAlchemy + PostgreSQL + auth + Redis + frontend
efa create myapp --no-interactive \
  --project-name myapp --package-name myapp \
  --frontend \
  --database --orm sqlalchemy --db-dialect postgres \
  --auth --redis
```

</details>

## 📁 Generated Project Preview

```
myapp/
├── backend/
│   ├── app/
│   │   ├── main.py          # Entry: EasyFastAPI + use() chain
│   │   ├── models/          # Data models
│   │   ├── routers/         # Routes
│   │   └── schemas/         # Pydantic schemas
│   ├── easy-fastapi.yaml    # Configuration
│   └── pyproject.toml
└── frontend/                # fullstack mode
    ├── packages/api-sdk/    # OpenAPI auto-generated SDK
    └── apps/                # Your frontend apps
```

## ⌨️ CLI Reference

### Common Commands

| Command | Description |
|---------|-------------|
| `efa create [TARGET] [OPTIONS]` | Create project (interactive/non-interactive) |
| `efa run [--host] [--port] [--reload]` | Start uvicorn |
| `efa db init` | Initialize migration config |
| `efa db migrate` | Generate migration files |
| `efa db upgrade` | Apply migrations |
| `efa db sync` | Create tables directly (dev) |
| `efa gen [--force]` | Generate CRUD code from models |

### `efa create` Options

| Option | Description | Default |
|--------|-------------|---------|
| `--no-interactive` | Skip interactive wizard | Interactive |
| `--project-name` | Project name | — |
| `--package-name` | Python package name | — |
| `--language` | Language (zh/en) | zh |
| `--database` | Enable database | false |
| `--orm` | ORM (tortoise/sqlalchemy/sqlmodel) | — |
| `--db-dialect` | Database dialect (mysql/postgres/sqlite) | — |
| `--migration` | Enable migrations | false |
| `--auth` | Enable authentication | false |
| `--redis` | Enable Redis | false |
| `--frontend` | Enable frontend | false |
| `--static` | Enable static file serving | false |

## 🧩 Extensions

| Extension | Description |
|-----------|-------------|
| `orm.tortoise` | Tortoise ORM data layer |
| `orm.sqlalchemy` | SQLAlchemy ORM data layer |
| `orm.sqlmodel` | SQLModel ORM data layer |
| `auth` | JWT + argon2 auth, zero ORM coupling |
| `redis` | Redis persistence, `enabled=false` falls back to memory |
| `i18n` | Internationalization (gettext + contextvars) |
| `static` | Static file serving |

> All three ORM extensions share the ORM-agnostic `database` config section. See [Extensions docs](docs/extensions.md) for service keys and config details.

## ⚙️ Configuration

Generated project's `easy-fastapi.yaml`:

```yaml
fastapi:
  root_path: /api

# After enabling ORM, extensions read the ORM-agnostic database section
database:
  dialect: sqlite
  database: db.sqlite3
# auth:
#   secret: your-secret-key
#   access_expire_minutes: 1440
# redis:
#   url: redis://localhost:6379/0
```

Environment variable override: `EFA_<SECTION>__<FIELD>` (e.g., `EFA_EASY_FASTAPI__AUTH__SECRET=prod-key`).

## 📖 Documentation

- [Quickstart](docs/quickstart.md)
- [CLI Reference](docs/cli.md)
- [Extensions](docs/extensions.md)
- [Architecture](docs/architecture.md)
- [0.x → 1.0 Migration Guide](docs/migration/0.x-to-1.0.md)

## License

MIT
