"""交互向导测试（questionary 收集选项，≥8 用例）。"""

import easy_fastapi_cli.scaffold.wizard as wiz


class FakeAnswers:
    """模拟 questionary 链式调用的返回预设答案。"""

    def __init__(self, answers):
        self._answers = list(answers)
        self._i = 0

    def ask(self):
        v = self._answers[self._i]
        self._i += 1
        return v

    def unsafe_ask(self):
        return self.ask()


def make_fake_questionary(answers):
    """返回一个 fake questionary，每次调用方法 pop 一个答案。"""
    state = {"i": 0}

    def _next():
        v = answers[state["i"]]
        state["i"] += 1
        return v

    def fake_text(msg, default=None):
        return FakeAnswers([_next()])

    def fake_select(msg, choices, default=None):
        return FakeAnswers([_next()])

    def fake_confirm(msg, default=False):
        return FakeAnswers([_next()])

    def fake_checkbox(msg, choices):
        return FakeAnswers([_next()])

    class Q:
        text = staticmethod(fake_text)
        select = staticmethod(fake_select)
        confirm = staticmethod(fake_confirm)
        checkbox = staticmethod(fake_checkbox)

    return Q


# run_wizard 调用顺序（frontend=True, database=True 全路径）：
# project_name(text), package_name(text), language(select),
# frontend(confirm), database(confirm),
# [orm(select), dialect(select), migration(confirm), auth(confirm) if database],
# redis(confirm), static(confirm), i18n(confirm)
# → 全路径 12 个答案（project, pkg, lang, frontend, database, orm, dialect,
#   migration, auth, redis, static, i18n = 12）


def test_wizard_returns_options_minimal(monkeypatch):
    # 最小路径：project, pkg, lang, frontend(=F), database(=F), redis(=F), static(=F), i18n(=F)
    monkeypatch.setattr(
        wiz,
        "questionary",
        make_fake_questionary(["demo", "demo", "zh", False, False, False, False, False]),
    )
    o = wiz.run_wizard()
    assert o.project_name == "demo"
    assert o.package_name == "demo"
    assert o.language == "zh"
    assert o.frontend is False
    assert o.database is False
    assert o.redis is False
    assert o.i18n is False


def test_wizard_fullstack(monkeypatch):
    # 全路径 12 个答案
    monkeypatch.setattr(
        wiz,
        "questionary",
        make_fake_questionary(
            [
                "demo",  # project_name
                "demo",  # package_name
                "en",  # language
                True,  # frontend
                True,  # database
                "tortoise",  # orm
                "mysql",  # dialect
                True,  # migration
                False,  # auth
                False,  # redis
                False,  # static
                True,  # i18n
            ]
        ),
    )
    o = wiz.run_wizard()
    assert o.frontend is True
    assert o.orm == "tortoise"
    assert o.db_dialect == "mysql"
    assert o.migration is True
    assert o.auth is False
    assert o.language == "en"
    assert o.i18n is True


def test_wizard_i18n_enabled(monkeypatch):
    monkeypatch.setattr(
        wiz,
        "questionary",
        make_fake_questionary(["p", "p", "zh", False, False, False, False, True]),
    )
    o = wiz.run_wizard()
    assert o.i18n is True


def test_wizard_package_name_defaults_from_project(monkeypatch):
    # project 给值，package_name 给空串 → 用 slug(project_name)
    monkeypatch.setattr(
        wiz,
        "questionary",
        make_fake_questionary(["My Project", "", "zh", False, False, False, False, False]),
    )
    o = wiz.run_wizard()
    assert o.project_name == "My Project"
    assert o.package_name == "my_project"  # slug 化


def test_wizard_project_name_falls_back_to_default(monkeypatch):
    # 传 default_project_name + 项目名留空 → 回退到默认；包名随之 slug 化
    monkeypatch.setattr(
        wiz,
        "questionary",
        make_fake_questionary(["", "", "zh", False, False, False, False, False]),
    )
    o = wiz.run_wizard(default_project_name="easy_fastapi_test")
    assert o.project_name == "easy_fastapi_test"
    assert o.package_name == "easy_fastapi_test"  # slug(默认名)


def test_wizard_project_name_explicit_overrides_default(monkeypatch):
    # 显式输入项目名应覆盖默认值
    monkeypatch.setattr(
        wiz,
        "questionary",
        make_fake_questionary(["myapi", "myapi", "zh", False, False, False, False, False]),
    )
    o = wiz.run_wizard(default_project_name="easy_fastapi_test")
    assert o.project_name == "myapi"
    assert o.package_name == "myapi"


def test_wizard_database_without_frontend(monkeypatch):
    # backend-only + database
    monkeypatch.setattr(
        wiz,
        "questionary",
        make_fake_questionary(["p", "p", "zh", False, True, "sqlalchemy", "sqlite", True, False, False, False, False]),
    )
    o = wiz.run_wizard()
    assert o.frontend is False
    assert o.database is True
    assert o.orm == "sqlalchemy"
    assert o.db_dialect == "sqlite"
    assert o.migration is True


def test_wizard_auth_enabled(monkeypatch):
    monkeypatch.setattr(
        wiz,
        "questionary",
        make_fake_questionary(["p", "p", "zh", False, True, "tortoise", "postgres", True, True, False, False, False]),
    )
    o = wiz.run_wizard()
    assert o.auth is True
    assert o.orm == "tortoise"
    assert o.db_dialect == "postgres"


def test_wizard_redis_enabled(monkeypatch):
    monkeypatch.setattr(
        wiz,
        "questionary",
        make_fake_questionary(["p", "p", "zh", False, False, True, False, False]),
    )
    o = wiz.run_wizard()
    assert o.redis is True
    assert o.database is False


def test_wizard_static_enabled(monkeypatch):
    monkeypatch.setattr(
        wiz,
        "questionary",
        make_fake_questionary(["p", "p", "zh", False, False, False, True, False]),
    )
    o = wiz.run_wizard()
    assert o.static is True


def test_wizard_returns_create_options_instance(monkeypatch):
    from easy_fastapi_cli.scaffold.options import CreateOptions

    monkeypatch.setattr(
        wiz,
        "questionary",
        make_fake_questionary(["p", "p", "zh", False, False, False, False, False]),
    )
    o = wiz.run_wizard()
    assert isinstance(o, CreateOptions)
