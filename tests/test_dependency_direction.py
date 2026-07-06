"""守护测试：runtime 包源码不得 import easy_fastapi_cli（依赖方向单向性）。"""

from pathlib import Path


def test_runtime_does_not_import_cli():
    """扫描 runtime 包所有 .py，断言无 easy_fastapi_cli import。"""
    runtime_src = Path("packages/easy_fastapi/src/easy_fastapi")
    if not runtime_src.exists():
        # 如果路径变了，测试失败提醒维护者更新路径
        raise AssertionError(f"runtime 源码目录不存在：{runtime_src}")

    violations = []
    for py_file in runtime_src.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "easy_fastapi_cli" in stripped:
                violations.append(f"{py_file}:{i}: {stripped}")

    assert not violations, (
        "runtime 包不得 import easy_fastapi_cli（依赖方向单向：CLI→runtime，不可反向）：\n" + "\n".join(violations)
    )
