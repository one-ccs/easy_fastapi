# Easy FastAPI

基于 FastAPI 开发的后端框架，集成了 Tortoise ORM、Pydantic、Aerich、PyJWT、PyYAML、Redis 等插件，并且可以在编写好 `models` 文件后执行 `manager.py gen` 命令，批量生成 `schemas`、`routers`、`services` 代码，旨在提供一个高效、易用的后端开发环境。该框架通过清晰的目录结构和模块化设计，大大减少了项目的前期开发工作，帮助开发者快速构建和部署后端服务。

![alt text](easy_fastapi/templates/frontend/assets/image/preview.png)

## 一、主要特点

1. 集成多种插件：集成了 Tortoise（数据库 ORM）、Pydantic（数据验证和序列化）、Aerich（数据库迁移）、PyJWT（JWT 认证）、PyYAML（项目配置读取）、Redis（登出黑名单） 等常用插件，提升开发效率。
2. 清晰的目录结构：通过明确的目录划分，如核心配置、数据库模型、路由、数据结构、事务处理和工具函数等，使项目结构清晰，便于维护和扩展。
3. 认证授权：内置认证授权模块，支持 JWT 认证，保障系统安全。
4. 数据库迁移支持：利用 Alembic 进行数据库迁移，支持自动生成迁移文件和更新数据库，确保数据库结构与代码同步。
5. 代码生成器：使用内置的代码生成器，在编写好 `models` 的前提下，意一键生成基本 CRUD 接口，大大减轻前期开发工作

## 二、目录结构说明

```plaintext
project-root/
│
├─ backend/  # 后端项目目录（python 3.10.15）
│   ├─ app/      # fastapi 项目目录
│   │   │
│   │   ├─ handlers/     # 处理器目录
│   │   │   ├─ authentication.py         # 认证处理器
│   │   │   ├─ exception.py              # 异常处理器
│   │   │   └─ ...
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
│   │   │   └─ ...
│   │   │
│   │   ├─ __init__.py      # 导入路、初始化配置、导入错误处理
│   │   └─ main.py          # 程序入口
│   │
│   ├─ logs/ # 日志目录
│   │   ├─  access.log      # 访问日志
│   │   └─  default.log     # 默认日志
│   │
│   ├─ test/  # 测试目录
│   │   └─  test_*.py       # 测试文件
│   │
│   ├─ easy_fastapi.yaml    # 项目配置
│   └─ log_config.json      # uvicorn 日志配置
│
├─ frontend/ # 前端项目目录
│   └─ ...
│
└─ ...
```

## 三、规约

1. 所有非 200 响应均 raise 对应异常

正例：

```python
if not await verify_password(form_data.password, user.h_pwd):
        raise FailureException('密码错误')
```

反例：

```python
if not await verify_password(form_data.password, user.h_pwd):
        return JSONResult.failure('密码错误')
```

## 四、部署

1. 安装依赖 `pip install easy_fastapi`
2. 初始化项目 `easy_fastapi init`
3. 启动项目
   1. 切换工作目录 `cd <项目名称>/backend`
   2. 启动项目
      - 开发环境: `easy_fastapi run --reload` 等价于 `uvicorn app:app --reload`
      - 生产环境: `easy_fastapi run` 等价于 `uvicorn app:app --log-config log_config.json --log-level warning`

## 五、开发

> 注：所有脚手架命令均在 `<项目名称>/backend` 目录下执行。

1. 修改 `backend/app/easy_fastapi.yaml` 中相关配置
2. 添加或修改 `backend.app.models` 中的模型
   1. 执行代码生成器 `easy_fastapi gen` 生成基本业务代码
   2. 根据实际清空添加或修改业务代码
3. 创建数据库
4. 初始化数据库
   1. 初始化 Aerich 配置 `easy_fastapi db init`
   2. 初始化数据库 `easy_fastapi db init-db`
   3. 初始化表 `easy_fastapi db init-table`

## 六、测试

1. 在 `backend/test` 目录中添加测试文件
2. 运行 `cd backend && pytest test` 查看测试结果

## 七、附录

### 1. 配置模板

```yaml
# 项目配置文件
# 请在此文件中配置项目相关信息，如数据库连接信息、安全认证配置、日志配置等
# 带 * 号表示必选项

easy_fastapi:
    # 是否强制所有除 500 外的状态码都返回 200 状态码，默认 False
    force_200_code: False
    # 上传文件保存目录
    upload_dir: ./upload
    # 单页应用配置
    spa:
        # 是否挂载单页应用，默认 False
        enabled: True
        # 入口文件路径
        index_file: ../frontend/index.html
        # 静态资源目录
        static_dir: ../frontend/assets
        # 静态资源 URL
        static_url: /assets
    # 安全认证配置
    authentication:
        # * 密钥
        secret_key: easy_fastapi
        # 令牌签发者, 默认 easy_fastapi
        iss: easy_fastapi
        # 认证令牌 URL, 默认 /auth/token
        token_url: /token
        # 登录 URL, 默认 /auth/login
        login_url: /login
        # 刷新令牌 URL, 默认 /auth/refresh
        refresh_url: /refresh
        # 算法，默认 HS256
        algorithm: HS256
        # 访问令牌过期时间，默认 15 分钟
        access_token_expire_minutes: 30
        # 刷新令牌过期时间，默认 10080 分钟，即 7 天
        refresh_token_expire_minutes: 10080


fastapi:
    # root_path，默认 ''
    root_path: /api
    # 文档配置，需在 fastapi 实例化时手动传参
    swagger:
        # 文档标题
        title: Easy FastAPI
        # 文档描述
        description: 基于 FastAPI 开发的后端框架，集成了 Tortoise ORM、Pydantic、Aerich、PyJWT、PyYAML、Redis 等插件，旨在提供一个高效、易用的后端开发环境。该框架通过清晰的目录结构和模块化设计，帮助开发者快速构建和部署后端服务。
        # 文档版本
        version: ~
        # 联系信息
        contact:
            # 联系人
            name: one-ccs
            # 联系人 URL
            url: ~
            # 联系人邮箱
            email: one-ccs@foxmail.com
        # 许可证信息
        license:
            # 许可证名称
            name: 开源协议：MIT
            # 许可证 URL
            url: https://github.com/one-ccs/easy_fastapi?tab=MIT-1-ov-file#readme
        # 用于获取访问令牌的 URL，默认 /token
        token_url: /token
        # 默认 /docs
        docs_url: /api-docs
        # 默认 /redoc
        redoc_url: /api-redoc
        # 默认 /openapi.json
        openapi_url: /api-json
    # 中间件配置
    middleware:
        # 跨域配置
        cors:
            # 是否启用跨域，默认 False
            enabled: False
            # 允许的域列表，默认 ['*']
            allow_origins:
                - '*'
            # 是否允许请求携带 cookie，默认 True
            allow_credentials: True
            # 允许的请求方法，默认 ['*']
            allow_methods:
                - '*'
            # 允许的请求头，默认 ['*']
            allow_headers:
                - '*'
        # 强制所有传入请求必须是 https 或 wss
        https_redirect:
            enabled: False
        # 强制所有传入请求都必须正确设置 Host 请求头，以防 HTTP 主机头攻击
        trusted_host:
            enabled: False
            allowed_hosts:
                - '*'
        # gzip 压缩配置
        gzip:
            enabled: False
            minimum_size: 1000
            compresslevel: 5


# 数据库配置
database:
    # * 数据库用户名
    username: root
    # * 数据库密码
    password: '123456'
    # * 数据库名称
    database: easy_fastapi
    # 数据库主机名，默认 127.0.0.1
    host: 127.0.0.1
    # 数据库端口号，默认 3306
    port: 3306
    # 是否打印日志，默认 False
    echo: False
    # 时区，默认 Asia/Chongqing
    timezone: Asia/Chongqing


# Redis 配置
redis:
    # 是否启用，默认 False
    enabled: False
    # * 主机名，默认 None
    host: 127.0.0.1
    # 密码，默认 None
    password: ~
    # 端口号，默认 6379
    port: 6379
    # 数据库号，默认 0
    db: 0
    # 是否解码响应，默认 True
    decode_responses: True
```
