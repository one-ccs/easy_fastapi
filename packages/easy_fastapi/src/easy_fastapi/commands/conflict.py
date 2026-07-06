"""gen 冲突（冲突报错，不静默覆盖）。"""


class GenConflictError(Exception):
    """目标文件已存在且未指定 --force。"""
