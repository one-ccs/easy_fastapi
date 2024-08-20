# Easy FastAPI

基于 FastAPI 开发的后端框架，集成 SQLAlchemy、Pydantic、Alembic 等插件。

## 一、目录结构说明

```plaintext
project-root/
│
├─ backend/  # 后端项目目录（python 3.12.4）
│   ├─ app/      # fastapi 项目目录
│   │   ├─ alembic/  # 数据迁移目录
│   │   │   ├─ versions # 数据库迁移文件
│   │   │   ├─ env.py   # 环境配置文件
│   │   │   ├─ ...
│   │   │
│   │   ├─ exceptions/ # 错误处理目录
│   │   │   ├─ exception_handler.py # 错误处理器
│   │   │   ├─ *_exception.py       # 自定义错误类
│   │   │   ├─ ...
│   │   │
│   │   ├─ models/     # 数据库模型目录
│   │   │   ├─ crud         # 数据库 crud 函数目录
│   │   │   │   ├─ *_crud.py        # 对应类的数据库操作函数
│   │   │   │   ├─ ...
│   │   │   │
│   │   │   ├─ *.py         # 数据库模型（user、role 等）
│   │   │   ├─ ...
│   │   │
│   │   ├─ routers/    # 路由目录（定义路由相关信息）
│   │   │   ├─ *_router.py  # 路由（user_router、role_router 等）
│   │   │   ├─ ...
│   │   │
│   │   ├─ schemas/    # pydantic 数据结构目录（定义请求响应参数结构）
│   │   │   ├─ *_schema.py  # 参数结构定义
│   │   │   ├─ ...
│   │   │
│   │   ├─ services/   # 事务处理目录（实现路由对应的逻辑）
│   │   │   ├─ *_service.py # 事务逻辑处理函数（user_service 等）
│   │   │   ├─ ...
│   │   │
│   │   ├─ utils/      # 工具函数目录
│   │   │   ├─ crud_utils # 数据库 crud 工具函数
│   │   │   │   ├─ result.py        # 响应体数据类
│   │   │   │   ├─ datetime_util.py # 日期时间相关工具类
│   │   │   │   ├─ path_util.py     # 路径相关工具类
│   │   │   │   ├─ *_util.py        # 与 models 对应的 curd 工具函数
│   │   │   │   ├─ ...
│   │   │
│   │   ├─ __init__.py # 导入路由并单独导入错误处理包
│   │   ├─ alembic.ini # 数据库迁移配置文件
│   │   ├─ config.py   # 配置文件
│   │   ├─ main.py     # 程序入口
│   │   ├─ requirements.txt # 依赖列表
│   │
│   ├─ db/ # 数据库文件目录
│   │   ├─  easy_fastapi.sql
│
├─ frontend/ # 前端项目目录
│   │ ...
│
├─ readme.md # 工程自述
├─ ...
```

## 二、部署

1. 安装依赖
2. 修改 `DB_PASS`
3. 修改 `ROOT_NAME`
4. 初始化数据库
5. 启动项目

## 数据库迁移插件 alembic

### 1、环境搭建

#### 1）初始化仓库

在后端项目目录中执行命令 `alembic init alembic` 创建一个名为 alembic 的仓库

#### 2）创建（ORM）类

略……

#### 3）修改配置文件

1. 注释 alembic.ini 中的 sqlalchemy.url
2. 修改 eny.py 文件

```python
# fileConfig(config.config_file_name)
fileConfig(config.config_file_name, encoding='utf-8')
```

```python
# target_metadata = None
import sys
sys.path.append(__file__[:__file__.index('backend') + len('backend')])
from app.models import Base
from app.config import Setting

target_metadata = Base.metadata
```

```python
def get_url():
    return str(Setting.DB_URI)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()
```

#### 4）生成迁移文件

使用命令 `alembic revision --autogenerate -m "message"` 可以将当前模型中的状态生成迁移文件。

#### 5）更新数据库

使用 `alembic upgrade head` 将刚刚生成的迁移文件，真正映射到数据库中。同理，如果要降级，那么使用 `alembic downgrade head` 。

#### 6）重复

如果以后修改了代码，则重复4~5的步骤。

### 2、命令和参数解释：

- init：创建一个 `alembic` 仓库。
- revision：创建一个新的版本文件。
- –-autogenerate：自动将当前模型的修改，生成迁移脚本。
- -m：本次迁移做了哪些修改，用户可以指定这个参数，方便回顾。
- upgrade：将指定版本的迁移文件映射到数据库中，会执行版本文件中的 `upgrade` 函数。如果有多个迁移脚本没有被映射到数据库中，那么会执行多个迁移脚本。
- [head]：代表最新的迁移脚本的版本号。
- downgrade：会执行指定版本的迁移文件中的 `downgrade` 函数。
- heads：展示head指向的脚本文件版本号。
- history：列出所有的迁移版本及其信息。
- current：展示当前数据库中的版本号。

另外，在你第一次执行 `upgrade` 的时候，就会在数据库中创建一个名叫 `alembic_version` 表，这个表只会有一条数据，记录当前数据库映射的是哪个版本的迁移文件

### QA

#### 1、编码错误

Q: UnicodeDecodeError: 'gbk' codec can't decode byte 0xa8 in position 2516: illegal multibyte sequence
A：将 `site-packages\alembic\util\compat.py` 的 `read_config_parser` 改为如下

```python
def read_config_parser(
    file_config: ConfigParser,
    file_argument: Sequence[Union[str, os.PathLike[str]]],
) -> List[str]:
    if py310:
        return file_config.read(file_argument, encoding="utf-8")
    else:
        return file_config.read(file_argument)
```
