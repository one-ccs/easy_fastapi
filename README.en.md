# Easy FastAPI — FastAPI Scaffold (1.0)

> Generate a full-stack FastAPI project with a single command: backend (3 ORMs × auth × Redis × static) + frontend (minimal pnpm monorepo skeleton + OpenAPI SDK auto-generation).

## Features

- **Dual-mode directory**: `backend-only` (API only) or `fullstack` (`backend/` + `frontend/` monorepo)
- **3 ORM choices**: Tortoise ORM / SQLAlchemy / SQLModel, unified `DbSession` / `UserModelProtocol` / `ModelIntrospector` protocols
- **Cross-ORM auth**: pwdlib (argon2 default) + PyJWT, zero ORM coupling
- **Redis extension**: override persistence, `enabled=false` falls back to memory
- **Frontend skeleton**: pnpm workspace monorepo, @hey-api/openapi-ts SDK generation, user creates apps in `frontend/apps/`
- **4 CLI commands + plugin extensions**: `efa create` / `efa run` / `efa db {init,migrate,upgrade,sync}` / `efa gen` + `efa i18n {init,compile,update}` (via CLIPlugin)
- **Optional dependency guards**: missing packages auto-hint `uv add <pkg>`
- **Strict config**: `easy-fastapi.yaml` + `ConfigLoader`, `extra='forbid'`, env overlay

## Installation

```bash
# Recommended: uv (CLI includes runtime)
uv tool install easy-fastapi-cli

# Or run temporarily
uvx efa --help
```

## Quick Start

### Interactive Creation (recommended for beginners)

```bash
efa create myapp
# Step-by-step: ORM, database dialect, auth, Redis, frontend, etc.
cd myapp
```

### Non-interactive Creation

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

cd myapp
```

### Start Backend

```bash
efa run              # Production mode
efa run --reload     # Development hot-reload
efa run --port 8080  # Custom port
```

Visit `http://localhost:8000/docs` for Swagger UI.

### Database Operations

```bash
efa db init      # Initialize migration config (non-idempotent, first run only)
efa db migrate   # Generate migration files
efa db upgrade   # Apply migrations
efa db sync      # Create tables directly (for development, no migrations)
```

### Code Generation

```bash
efa gen          # Generate router/schema/service from models
efa gen --force  # Overwrite existing files
```

### Frontend skeleton (fullstack projects)

The generated `frontend/` is a minimal pnpm monorepo skeleton: only `packages/api-sdk` (OpenAPI-generated SDK) + `apps/` (placeholder for your apps).

```bash
cd frontend
pnpm install      # Install dependencies
pnpm sdk:gen      # Generate SDK from backend OpenAPI (requires running backend)
# Create your own frontend app in frontend/apps/ (React/Vue/anything)
```

## CLI Reference

| Command | Description |
|---|---|
| `efa create [TARGET] [OPTIONS]` | Create project (interactive/non-interactive) |
| `efa run [--host] [--port] [--reload]` | Start uvicorn |
| `efa db init` | Initialize migration config |
| `efa db migrate` | Generate migration files |
| `efa db upgrade` | Apply migrations |
| `efa db sync` | Create tables directly |
| `efa gen [--force]` | Generate CRUD code |

### `efa create` Options

| Option | Description | Default |
|---|---|---|
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

## Extensions

| Extension | Service keys provided | Config section |
|---|---|---|
| `orm.tortoise` | `db_session_factory`, `model_introspector`, `user_model`, `role_model` | `database` |
| `orm.sqlalchemy` | `db_session_factory`, `model_introspector`, `user_model`, `role_model` | `database` |
| `orm.sqlmodel` | `db_session_factory`, `model_introspector`, `user_model`, `role_model` | `database` |
| `auth` | `token_service`, `require` | `auth` |
| `redis` | `persistence` (override) | `redis` |
| `i18n` | `i18n` | `i18n` |
| `static` | — | `static` |

> All three ORM extensions share the ORM-agnostic `database` section.

## Configuration

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

## Documentation

- [Quickstart](docs/quickstart.md)
- [CLI Reference](docs/cli.md)
- [Extensions](docs/extensions.md)
- [Architecture](docs/architecture.md)
- [Decisions & Constraints](docs/DECISIONS.md)
- [0.x → 1.0 Migration Guide](docs/migration/0.x-to-1.0.md)

## License

MIT
