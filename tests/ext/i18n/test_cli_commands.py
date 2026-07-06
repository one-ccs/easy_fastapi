"""i18n CLI 命令业务逻辑测试。"""

import pytest
from easy_fastapi.ext.i18n.cli_commands import do_compile, do_init, do_update


def test_do_init_creates_po_file(tmp_path):
    """do_init 创建 locales/{lang}/LC_MESSAGES/messages.po。"""
    do_init("zh_CN", project_dir=tmp_path)

    po_path = tmp_path / "locales" / "zh_CN" / "LC_MESSAGES" / "messages.po"
    assert po_path.exists()
    content = po_path.read_text(encoding="utf-8")
    assert "Language: zh_CN" in content
    assert 'msgid ""' in content  # PO header


def test_do_init_skips_existing(tmp_path, capsys):
    """目录和文件已存在时跳过不覆盖。"""
    do_init("zh_CN", project_dir=tmp_path)

    # 第二次调用
    do_init("zh_CN", project_dir=tmp_path)
    assert "已存在" in capsys.readouterr().out


def test_do_compile_creates_mo(tmp_path):
    """do_compile 编译 .po → .mo。"""
    # 先 init
    do_init("zh_CN", project_dir=tmp_path)

    # 添加一条翻译
    po_path = tmp_path / "locales" / "zh_CN" / "LC_MESSAGES" / "messages.po"
    content = po_path.read_text(encoding="utf-8")
    content += '\nmsgid "Hello"\nmsgstr "你好"\n'
    po_path.write_text(content, encoding="utf-8")

    do_compile(project_dir=tmp_path)

    mo_path = tmp_path / "locales" / "zh_CN" / "LC_MESSAGES" / "messages.mo"
    assert mo_path.exists()


def test_do_compile_skips_up_to_date(tmp_path, capsys):
    """do_compile 跳过已是最新（mtime 比对）的 .po。"""
    do_init("zh_CN", project_dir=tmp_path)
    do_compile(project_dir=tmp_path)

    # 第二次调用应跳过
    do_compile(project_dir=tmp_path)
    output = capsys.readouterr().out
    assert "跳过" in output


def test_do_compile_no_locales_dir(tmp_path):
    """找不到 locales/ 目录时报错提示。"""
    with pytest.raises(FileNotFoundError, match="locales"):
        do_compile(project_dir=tmp_path)


def test_do_update_adds_new_msgid(tmp_path):
    """do_update 扫描源码 _() 调用，添加新 msgid 到 .po。"""
    # 准备项目结构
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("", encoding="utf-8")
    (app_dir / "service.py").write_text(
        'from easy_fastapi import _\nmsg = _("User not found")\n',
        encoding="utf-8",
    )

    # 先 init
    do_init("zh_CN", project_dir=tmp_path)

    do_update(project_dir=tmp_path)

    po_path = tmp_path / "locales" / "zh_CN" / "LC_MESSAGES" / "messages.po"
    content = po_path.read_text(encoding="utf-8")
    assert 'msgid "User not found"' in content
    assert 'msgstr ""' in content  # 新增条目，msgstr 留空


def test_do_update_preserves_existing_translation(tmp_path):
    """do_update 保留已有翻译。"""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("", encoding="utf-8")
    (app_dir / "service.py").write_text(
        'from easy_fastapi import _\nmsg = _("Hello")\n',
        encoding="utf-8",
    )

    do_init("zh_CN", project_dir=tmp_path)

    # 手动添加一条翻译
    po_path = tmp_path / "locales" / "zh_CN" / "LC_MESSAGES" / "messages.po"
    content = po_path.read_text(encoding="utf-8")
    content += '\nmsgid "Hello"\nmsgstr "你好"\n'
    po_path.write_text(content, encoding="utf-8")

    do_update(project_dir=tmp_path)

    content = po_path.read_text(encoding="utf-8")
    assert 'msgstr "你好"' in content  # 保留翻译


def test_do_update_marks_obsolete(tmp_path):
    """do_update 将已删除的 msgid 标记为 obsolete（注释掉）。"""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("", encoding="utf-8")
    # 源码中没有 _() 调用
    (app_dir / "service.py").write_text("pass\n", encoding="utf-8")

    do_init("zh_CN", project_dir=tmp_path)

    # 手动添加一条 .po 条目（源码中已无引用）
    po_path = tmp_path / "locales" / "zh_CN" / "LC_MESSAGES" / "messages.po"
    content = po_path.read_text(encoding="utf-8")
    content += '\nmsgid "Old message"\nmsgstr "旧消息"\n'
    po_path.write_text(content, encoding="utf-8")

    do_update(project_dir=tmp_path)

    content = po_path.read_text(encoding="utf-8")
    # obsolete 条目被注释
    assert "#~ msgid" in content or "# obsolete" in content
    assert "旧消息" in content  # 保留翻译防误删


def test_do_update_no_locales_dir(tmp_path):
    """找不到 locales/ 目录时报错提示。"""
    with pytest.raises(FileNotFoundError, match="locales"):
        do_update(project_dir=tmp_path)


def test_do_update_escapes_quotes_and_newlines(tmp_path):
    """do_update 写入 .po 时转义 msgid/msgstr 中的双引号和换行符。"""
    from easy_fastapi.ext.i18n.cli_commands import _po_escape

    # 直接测试 _po_escape 转义函数
    assert _po_escape('He said "hello"') == 'He said \\"hello\\"'
    assert _po_escape("line1\nline2") == "line1\\nline2"
    assert _po_escape("tab\there") == "tab\\there"
    assert _po_escape("back\\slash") == "back\\\\slash"

    # 端到端：msgid 含双引号，update 后 .po 文件应能被 parse_po 正确解析回来
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("", encoding="utf-8")
    # 用单引号包裹的双引号 msgid
    (app_dir / "service.py").write_text(
        "from easy_fastapi import _\nmsg = _('He said \"hi\"')\n",
        encoding="utf-8",
    )

    do_init("zh_CN", project_dir=tmp_path)
    do_update(project_dir=tmp_path)

    po_path = tmp_path / "locales" / "zh_CN" / "LC_MESSAGES" / "messages.po"
    content = po_path.read_text(encoding="utf-8")
    # 写入时应转义双引号
    assert 'msgid "He said \\"hi\\""' in content

    # 验证 round-trip：parse_po 能正确解析回原 msgid
    from easy_fastapi.ext.i18n.msgfmt import parse_po

    entries = parse_po(po_path)
    assert ('He said "hi"', "") in entries
