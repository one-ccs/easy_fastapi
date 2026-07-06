"""可选第三方依赖统一守卫。

ext 模块 import 真实第三方包时统一经 require()，把缺依赖翻译成
含真实包名 + `uv add <包名>` 的中文 ExtensionError。
只翻译 ModuleNotFoundError；模块存在但内部执行报其它异常应原样抛出。
"""

import importlib

from .exceptions import ExtensionError

_MISSING_HINT = {
    "tortoise-orm": "uv add tortoise-orm",
    "sqlalchemy": "uv add sqlalchemy",
    "sqlmodel": "uv add sqlmodel",
    "aerich": "uv add aerich",
    "alembic": "uv add alembic",
    "pyjwt": "uv add pyjwt",
    "pwdlib": "uv add pwdlib",
    "redis": "uv add redis",
}


def _is_target_missing(missing_name: str, module_name: str) -> bool:
    """判断缺失的模块是否就是目标 module_name 本身或其父包/同级前缀。"""
    top = module_name.split(".")[0]
    missing_top = missing_name.split(".")[0]
    return missing_top == top


def _classify_missing(e: ModuleNotFoundError, module_name: str, package: str) -> str:
    """区分「目标模块/其父包缺失」与「子依赖缺失」，返回中文描述。"""
    missing = e.name or ""
    if _is_target_missing(missing, module_name):
        return f"缺少依赖 '{package}'（模块 '{module_name}'）"
    return f"依赖 '{package}' 所需的子依赖 '{missing}' 缺失（导入 '{module_name}' 时）"


def require(package: str, module_name: str):
    """导入模块；缺依赖时抛带 uv add 提示的 ExtensionError。

    只处理 ModuleNotFoundError；其它异常原样抛出不误包装。
    """
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        if e.name and not _is_target_missing(e.name, module_name):
            # 缺失的是子依赖而非目标本身 → 原样抛出
            raise
        target = _classify_missing(e, module_name, package)
        hint = _MISSING_HINT.get(package, f"uv add {package}")
        raise ExtensionError(f"{target}。\n请执行：  {hint}\n(原始错误: {e})") from e
