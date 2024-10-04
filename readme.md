# Easy FastAPI

基于 FastAPI 开发的后端框架，集成了 Tortoise ORM、Pydantic、Aerich、PyJWT、PyYAML、Redis 等插件，旨在提供一个高效、易用的后端开发环境。该框架通过清晰的目录结构和模块化设计，帮助开发者快速构建和部署后端服务。

![alt text](backend/preview/preview_1.jpeg)

## 一、主要特点

1. 集成多种插件：集成了 Tortoise（数据库 ORM）、Pydantic（数据验证和序列化）、Aerich（数据库迁移）、PyJWT（JWT 认证）、PyYAML（项目配置读取）、Redis（登出黑名单） 等常用插件，提升开发效率。
2. 清晰的目录结构：通过明确的目录划分，如核心配置、数据库模型、路由、数据结构、事务处理和工具函数等，使项目结构清晰，便于维护和扩展。
3. 认证授权：内置认证授权模块，支持 JWT 认证，保障系统安全。
4. 数据库迁移支持：利用 Alembic 进行数据库迁移，支持自动生成迁移文件和更新数据库，确保数据库结构与代码同步。

## 二、目录结构说明

```plaintext
project-root/
│
├─ backend/  # 后端项目目录（python 3.12.4）
│   ├─ app/      # fastapi 项目目录
│   │   ├─ core/  # 核心配置文件
│   │   │   ├─ exceptions/   # 异常类目录
│   │   │   │   └─ *_exception.py        # 自定义异常类
│   │   │   │
│   │   │   ├─ authorization.py     # 认证授权相关配置
│   │   │   ├─ config.py            # 项目配置
│   │   │   ├─ db.py                # 数据库配置
│   │   │   ├─ exception_handler.py # 异常处理配置
│   │   │   ├─ logger.py            # 日志配置
│   │   │   ├─ redis.py             # redis 配置
│   │   │   ├─ result.py            # 响应体数据类
│   │   │   └─ yaml.py              # yaml 配置
│   │   │
│   │   ├─ models/     # 数据库模型目录
│   │   │   ├─ *.py         # 数据库模型（user、role 等）
│   │   │   └─ ...
│   │   │
│   │   ├─ routers/    # 路由目录（定义路由相关信息）
│   │   │   ├─ *_router.py  # 路由（user_router、role_router 等）
│   │   │   └─ ...
│   │   │
│   │   ├─ schemas/    # pydantic 数据结构目录（定义请求响应参数结构）
│   │   │   ├─ *.py         # 参数模型
│   │   │   └─ ...
│   │   │
│   │   ├─ services/   # 事务处理目录（实现路由对应的逻辑）
│   │   │   ├─ *_service.py # 事务逻辑处理函数（user_service 等）
│   │   │   └─ ...
│   │   │
│   │   ├─ utils/      # 工具函数目录
│   │   │   ├─ crud_utils # 数据库 crud 工具函数
│   │   │   │   ├─ datetime_util.py # 日期时间相关工具类
│   │   │   │   ├─ object_util.py   # 对象相关工具类
│   │   │   │   ├─ path_util.py     # 路径相关工具类
│   │   │   │   ├─ string_util.py   # 字符串相关工具类
│   │   │   │   └─ ...
│   │   │   │
│   │   │
│   │   ├─ __init__.py      # 导入路、初始化配置、导入错误处理
│   │   ├─ easy_fastapi.py  # 配置文件
│   │   ├─ main.py          # 程序入口
│   │   └─ pyproject.toml   # Aerich 数据库迁移配置
│   │
│   ├─ logs/ # 日志目录
│   │   ├─  access.log      # 访问日志
│   │   └─  default.log     # 默认日志
│   │
│   ├─ test/  # 测试目录
│   │   ├─  test_authorization_router.py  # 认证授权测试文件
│   │   └─  test_*.py                     # 其他测试文件
│   │
│   ├─ manager.py               # 项目管理文件
│   ├─ requirements.txt         # 依赖列表
│   └─ uvicorn_log_config.json  # uvicorn 日志配置
│
├─ frontend/ # 前端项目目录
│   └─ ...
│
├─ license   # MIT 开源协议
├─ readme.md # 工程自述
└─ ...
```

## 三、规约

1. 所有非 200 响应均 raise 对应异常

正例：

```python
if not verify_password(form_data.password, user.hashed_password):
        raise FailureException('密码错误')
```

反例：

```python
if not verify_password(form_data.password, user.hashed_password):
        return Result.failure('密码错误')
```

## 四、部署

1. 安装依赖 `cd backend && pip install -r requirements.txt`
2. 修改 `backend/app/easy_fastapi.yaml` 中相关配置
3. 创建数据库
4. 初始化数据库
   1. 初始化 Aerich 配置 `manager.py db init`
   2. 初始化数据库 `manager.py db init-db`
   3. 初始化表 `manager.py db init-table`
5. 创建 `backend/logs` 目录
6. 启动项目
   - `uvicorn app:app --reload`
   - `uvicorn app:app --reload --log-config uvicorn_log_config.json --log-level info`
   - `manager.py run --reload`

## 五、测试

1. 在 `backend/test` 目录中添加测试文件
2. 运行 `cd backend/test && pytest` 查看测试结果
