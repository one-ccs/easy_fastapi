"""把 Manifest 落盘。

遍历 fragments：is_template=True 经 Renderer 渲染，False 原样拷贝。
逐文件写，自动建父目录。返回写入的绝对路径列表。
"""

from pathlib import Path

from .manifest import Manifest
from .options import CreateOptions
from .renderer import Renderer


def write_manifest(manifest: Manifest, options: CreateOptions, project_dir: Path, templates_root: Path) -> list[Path]:
    """落盘所有 fragment，返回写入的绝对路径列表。"""
    renderer = Renderer(options)
    project_dir = Path(project_dir)
    templates_root = Path(templates_root)
    written: list[Path] = []
    for frag in manifest.fragments:
        src = templates_root / frag.src
        dest = project_dir / frag.dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        if frag.is_template:
            try:
                content = renderer.render(src.read_text(encoding="utf-8"))
            except FileNotFoundError:
                raise RuntimeError(f"模板文件不存在：{src}（fragment dest={frag.dest}）") from None
            dest.write_text(content, encoding="utf-8")
        else:
            dest.write_bytes(src.read_bytes())
        written.append(dest)
    return written
