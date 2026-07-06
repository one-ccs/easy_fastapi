"""模板目录遍历 helper（遍历模式）。

遍历模板子树，展开为 Fragment 列表：
- .j2 结尾 → is_template=True，dest 去掉 .j2
- 其他 → is_template=False，原样拷贝
- dest = dest_prefix + 相对路径（去 .j2）
"""

from pathlib import Path

from .manifest import Fragment


def walk_tree(src_root: Path, *, dest_prefix: str = "", templates_root: Path | None = None) -> list[Fragment]:
    """遍历模板子树，展开为 Fragment 列表。

    Args:
        src_root: 要遍历的模板目录（如 templates/frontend/）
        dest_prefix: dest 前缀（如 "frontend/"），落盘时加到每个文件路径前
        templates_root: 用于计算 Fragment.src 相对路径的根；默认 = src_root
    """
    templates_root = templates_root or src_root
    frags: list[Fragment] = []
    for path in sorted(src_root.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(src_root).as_posix()
        is_template = rel.endswith(".j2")
        dest_name = rel[:-3] if is_template else rel
        dest = f"{dest_prefix}{dest_name}" if dest_prefix else dest_name
        src_rel = path.relative_to(templates_root).as_posix()
        frags.append(Fragment(src=src_rel, dest=dest, is_template=is_template))
    return frags
