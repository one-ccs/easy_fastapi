# 快速上手

5 分钟从零创建并运行一个 Easy FastAPI 项目。

## 前置

- Python ≥ 3.10
- [uv](https://docs.astral.sh/uv/)（包管理器）
- Node.js ≥ 18 + pnpm ≥ 9（仅前端项目需要）

## 1. 安装

```bash
uv tool install easy-fastapi-cli
# 验证
efa --help
```

## 2. 创建项目

### 交互式（推荐）

```bash
efa create demo
```

按向导选择：项目名、ORM、数据库方言、是否启用认证/Redis/迁移/前端/静态。

### 非交互式

```bash
efa create demo --no-interactive \
  --project-name demo --package-name demo \
  --database --orm tortoise --db-dialect sqlite --auth

cd demo
```

## 3. 数据库

```bash
# 开发用：直接建表（无需迁移）
efa db sync

# 或用迁移：
efa db init      # 首次初始化
efa db migrate   # 生成迁移
efa db upgrade   # 应用
```

## 4. 运行后端

```bash
efa run --reload
```

访问：
- Swagger：`http://localhost:8000/docs`
- OpenAPI JSON：`http://localhost:8000/openapi.json`

## 5. 生成 CRUD 代码

编辑 `backend/app/models/user.py` 添加模型字段后：

```bash
efa gen          # 生成 router/schema/service
efa gen --force  # 覆盖已有
```

## 6. 前端骨架（仅 fullstack 项目）

生成的 `frontend/` 是最小 pnpm monorepo 骨架：仅含 `packages/api-sdk`（OpenAPI 生成的 SDK）+ `apps/`（你自建应用的占位）。不预置具体前端应用。

```bash
cd frontend
pnpm install

# 生成 API SDK（需先启动后端 efa run）
pnpm sdk:gen
```

在 `frontend/apps/` 下自行创建前端应用（React/Vue/任意），通过 workspace 依赖引用 `api-sdk`：

```bash
cd apps
pnpm create vite my-app   # 示例
```

## 7. 测试

项目内 `pytest` 运行已有测试。

## 下一步

- [CLI 参考](cli.md)
- [扩展](extensions.md)
- [架构](architecture.md)
- [关键决策与约束](DECISIONS.md)
