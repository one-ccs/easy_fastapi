"""efa create 命令。

流程：check_target（目录冲突先检，非空需用户确认）
     → 交互或参数取 options → apply_defaults → validate
     → build_manifest → write_manifest → write_marker。

冲突策略（conflict.check_target 返回 ConflictResult）：
- empty：直接创建
- whitelist_only（in_place 仅白名单）：警告语气，询问是否继续
- blocked（含非白名单或非 in_place 非空）：错误语气，禁止创建
"""

from pathlib import Path

import typer

from easy_fastapi_cli.scaffold.conflict import WHITELIST_IN_PLACE, check_target
from easy_fastapi_cli.scaffold.manifest import Manifest, build_manifest
from easy_fastapi_cli.scaffold.marker import write_marker
from easy_fastapi_cli.scaffold.validate import apply_defaults, validate
from easy_fastapi_cli.scaffold.wizard import confirm_options, options_from_args, run_wizard
from easy_fastapi_cli.scaffold.write import write_manifest


def _templates_root() -> Path:
    """经 importlib.resources 定位包内 templates 目录（不依赖 cwd）。"""
    from importlib.resources import files

    return Path(str(files("easy_fastapi_cli") / "templates"))


def _resolve_target_conflict(result, *, in_place: bool, interactive: bool, target: str) -> None:
    """处理 check_target 结果：blocked 抛错，whitelist_only 需用户确认。

    whitelist_only 在 interactive 模式下询问用户；非交互模式默认拒绝（除非调用方自行强制）。
    """
    if result.status == "empty":
        return

    if result.status == "blocked":
        if in_place:
            raise typer.BadParameter(
                f"当前目录存在非白名单文件：{result.offenders}，禁止创建。\n"
                f"in_place 模式仅允许共存：{sorted(WHITELIST_IN_PLACE)}。\n"
                "请清理目录或换用空目录后重试。"
            )
        raise typer.BadParameter(
            f"目标目录非空：{target}（efa create <NAME> 要求目标为空；如需在当前目录生成请用 efa create .）"
        )

    # whitelist_only：警告并询问
    if not interactive:
        # 非交互模式：无法询问，默认拒绝以防误覆盖
        raise typer.BadParameter(
            f"当前目录已含文件（均为白名单：{sorted(result.whitelisted)}）。\n"
            "非交互模式默认不覆盖，请改用交互模式或在空目录执行。"
        )

    import questionary

    confirmed = questionary.confirm(
        f"⚠️  当前目录已存在文件：{sorted(result.whitelisted)}（均为白名单条目）。\n继续创建将覆盖同名文件。是否继续？",
        default=False,
    ).ask()
    if not confirmed:
        raise typer.Exit(code=1)


def do_create(
    target: str, *, interactive: bool, project_name: str | None, package_name: str | None, **flags
) -> tuple[Path, Manifest]:
    """执行 create 全流程，返回项目根目录与清单。"""
    in_place = target in (".", "./")
    project_dir = Path(target).resolve()
    # 未显式传 --project-name 时，从目标目录名推导（in_place 取 cwd 名）
    if not project_name:
        project_name = project_dir.name

    # ── 1. 先检查目标目录冲突（在收集选项之前，避免用户白填一堆） ──
    result = check_target(project_dir, in_place=in_place)
    _resolve_target_conflict(result, in_place=in_place, interactive=interactive, target=target)

    # ── 2. 收集选项 ──
    if interactive:
        options = run_wizard(default_project_name=project_name)
        if not confirm_options(options):
            raise typer.Exit(code=1)
    else:
        kwargs = {k: v for k, v in flags.items() if v is not None}
        options = options_from_args(project_name=project_name, package_name=package_name, **kwargs)

    options = apply_defaults(options)
    options = validate(options)

    # ── 3. 落盘 ──
    project_dir.mkdir(parents=True, exist_ok=True)

    templates_root = _templates_root()
    manifest = build_manifest(options, templates_root=templates_root)
    write_manifest(manifest, options, project_dir, templates_root)

    # 版本从各包 __version__ 动态获取（同版同发）
    from easy_fastapi import __version__ as easy_fastapi_version

    from easy_fastapi_cli import __version__ as template_version

    write_marker(project_dir, options, easy_fastapi_version=easy_fastapi_version, template_version=template_version)
    return project_dir, manifest
