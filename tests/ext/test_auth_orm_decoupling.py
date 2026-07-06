"""静态断言 ext/auth 零 import 具体 ORM。"""

from pathlib import Path

# 任何对具体 ORM 模块的直接 import 都是耦合（auth 应全走注入的 service 协议）
FORBIDDEN = (
    "import tortoise",
    "from tortoise",
    "import sqlalchemy",
    "from sqlalchemy",
    "import sqlmodel",
    "from sqlmodel",
)

_AUTH_DIR = Path(__file__).resolve().parents[2] / "packages" / "easy_fastapi" / "src" / "easy_fastapi" / "ext" / "auth"


def test_auth_does_not_import_orm():
    auth_dir = _AUTH_DIR
    offenders = []
    for py in auth_dir.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for token in FORBIDDEN:
            if token in text:
                offenders.append(f"{py.name}: {token}")
    assert not offenders, f"auth 扩展耦合了具体 ORM：{offenders}"


def test_auth_source_files_exist():
    auth_dir = _AUTH_DIR
    py_files = {p.name for p in auth_dir.rglob("*.py")}
    assert "hasher.py" in py_files
    assert "token.py" in py_files
    assert "extension.py" in py_files
    assert "decorator.py" in py_files
    assert "schemas.py" in py_files
    assert "config.py" in py_files
