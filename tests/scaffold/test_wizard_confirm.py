"""向导确认页测试（rich 摘要+二次确认，≥8 用例）。"""

import easy_fastapi_cli.scaffold.wizard as wiz
from easy_fastapi_cli.scaffold.options import CreateOptions


def _mk(**kw):
    base = {"project_name": "demo", "package_name": "demo"}
    base.update(kw)
    return CreateOptions(**base)


class FakeConfirm:
    def __init__(self, answer):
        self._answer = answer

    def ask(self):
        return self._answer

    def unsafe_ask(self):
        return self._answer


# ── 1. 确认 → True ──


def test_confirm_yes(monkeypatch):
    o = _mk()
    monkeypatch.setattr(wiz.questionary, "confirm", lambda msg, default=True: FakeConfirm(True))
    assert wiz.confirm_options(o) is True


# ── 2. 否认 → False ──


def test_confirm_no(monkeypatch):
    o = _mk()
    monkeypatch.setattr(wiz.questionary, "confirm", lambda msg, default=True: FakeConfirm(False))
    assert wiz.confirm_options(o) is False


# ── 3. 返回 bool 类型 ──


def test_confirm_returns_bool(monkeypatch):
    o = _mk()
    monkeypatch.setattr(wiz.questionary, "confirm", lambda msg, default=True: FakeConfirm(True))
    result = wiz.confirm_options(o)
    assert isinstance(result, bool)


# ── 4. 不同选项确认 True ──


def test_confirm_with_full_options(monkeypatch):
    o = _mk(
        frontend=True,
        database=True,
        orm="tortoise",
        db_dialect="mysql",
        auth=True,
        redis=True,
    )
    monkeypatch.setattr(wiz.questionary, "confirm", lambda msg, default=True: FakeConfirm(True))
    assert wiz.confirm_options(o) is True


# ── 5. 不同选项确认 False ──


def test_confirm_full_options_false(monkeypatch):
    o = _mk(database=True, orm="sqlalchemy", db_dialect="sqlite")
    monkeypatch.setattr(wiz.questionary, "confirm", lambda msg, default=True: FakeConfirm(False))
    assert wiz.confirm_options(o) is False


# ── 6. rich 打印不抛异常（副作用验证）──


def test_confirm_rich_print_no_error(monkeypatch, capsys):
    o = _mk()
    monkeypatch.setattr(wiz.questionary, "confirm", lambda msg, default=True: FakeConfirm(True))
    wiz.confirm_options(o)  # 不应抛异常


# ── 7. 多次调用不累积状态 ──


def test_confirm_multiple_calls(monkeypatch):
    o = _mk()
    call_count = 0

    def fake_confirm(msg, default=True):
        nonlocal call_count
        call_count += 1
        return FakeConfirm(call_count % 2 == 1)  # 奇数次 True，偶数次 False

    monkeypatch.setattr(wiz.questionary, "confirm", fake_confirm)
    assert wiz.confirm_options(o) is True
    assert wiz.confirm_options(o) is False


# ── 8. 空答案（None）→ False ──


def test_confirm_none_answer(monkeypatch):
    o = _mk()
    monkeypatch.setattr(wiz.questionary, "confirm", lambda msg, default=True: FakeConfirm(None))
    # bool(None) is False
    assert wiz.confirm_options(o) is False
