from io import StringIO
from pathlib import Path

from eraplay.cli import (
    check_project,
    compatibility_report,
    init_project,
    list_symbols,
    main,
    play_project,
    run_entry,
)

ROOT = Path(__file__).resolve().parents[1]


def test_check_project_reports_ok_for_fixtures() -> None:
    out = StringIO()

    exit_code = check_project(ROOT / "fixtures", out=out)

    assert exit_code == 0
    assert "OK:" in out.getvalue()
    assert "6 ERB" in out.getvalue()


def test_check_project_reports_diagnostics(tmp_path: Path) -> None:
    (tmp_path / "broken.erb").write_text("@EVENTFIRST\nCALL MISSING\n", encoding="utf-8")
    out = StringIO()

    exit_code = check_project(tmp_path, out=out)

    assert exit_code == 1
    assert "unresolved CALL target 'MISSING'" in out.getvalue()
    assert "1 diagnostic(s)" in out.getvalue()


def test_check_project_accepts_external_call_override(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text("@EVENTFIRST\nCALL MISSING\n", encoding="utf-8")
    out = StringIO()

    exit_code = check_project(tmp_path, out=out, external_calls=("MISSING",))

    assert exit_code == 0
    assert "OK:" in out.getvalue()


def test_main_check_command() -> None:
    assert main(["check", str(ROOT / "fixtures")]) == 0


def test_main_check_external_call_option(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text("@EVENTFIRST\nCALL MISSING\n", encoding="utf-8")

    assert main(["check", str(tmp_path), "--external-call", "MISSING"]) == 0


def test_list_symbols_reports_indexed_symbols() -> None:
    out = StringIO()

    exit_code = list_symbols(ROOT / "fixtures", out=out)
    text = out.getvalue()

    assert exit_code == 0
    assert "[label]" in text
    assert "EVENTFIRST" in text
    assert "[define]" in text
    assert "DEFAULT_MONEY" in text
    assert "[csv_key]" in text
    assert "\u30bf\u30a4\u30c8\u30eb" in text


def test_main_symbols_command() -> None:
    assert main(["symbols", str(ROOT / "fixtures")]) == 0


def test_compatibility_report_summarizes_ok_project() -> None:
    out = StringIO()

    exit_code = compatibility_report(ROOT / "fixtures", out=out)
    text = out.getvalue()

    assert exit_code == 0
    assert "Compatibility report:" in text
    assert "Diagnostics: 0" in text
    assert "Status: OK" in text


def test_compatibility_report_groups_unresolved_calls(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        "@EVENTFIRST\nCALL MISSING\nCALL MISSING\nCALL OTHER\n",
        encoding="utf-8",
    )
    out = StringIO()

    exit_code = compatibility_report(tmp_path, out=out, top=1)
    text = out.getvalue()

    assert exit_code == 0
    assert "Diagnostics: 3" in text
    assert "3: unresolved CALL" in text
    assert "2: MISSING" in text
    assert "1: OTHER" not in text


def test_main_compat_command_accepts_external_call(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text("@EVENTFIRST\nCALL MISSING\n", encoding="utf-8")

    assert main(["compat", str(tmp_path), "--external-call", "MISSING"]) == 0


def test_init_project_creates_config(tmp_path: Path) -> None:
    out = StringIO()

    exit_code = init_project(tmp_path, encoding="cp950", out=out)

    assert exit_code == 0
    assert (tmp_path / "eraplay.toml").exists()
    assert "created" in out.getvalue()


def test_init_project_refuses_existing_config(tmp_path: Path) -> None:
    init_project(tmp_path)
    out = StringIO()

    exit_code = init_project(tmp_path, out=out)

    assert exit_code == 1
    assert "config already exists" in out.getvalue()


def test_main_init_command(tmp_path: Path) -> None:
    assert main(["init", str(tmp_path), "--encoding", "cp932"]) == 0
    assert (tmp_path / "eraplay.toml").exists()


def test_run_entry_prints_output() -> None:
    out = StringIO()

    exit_code = run_entry(ROOT / "fixtures", out=out)

    assert exit_code == 0
    assert "hello" in out.getvalue()


def test_play_project_resumes_from_fake_input(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
PRINTL "[1] 通常業務"
INPUT
PRINTL "after input"
""",
        encoding="utf-8",
    )
    out = StringIO()
    inputs = iter(["1"])

    exit_code = play_project(tmp_path, out=out, input_func=lambda _prompt: next(inputs))

    text = out.getvalue()
    assert exit_code == 0
    assert "[actions]" in text
    assert "1: 通常業務" in text
    assert "after input" in text


def test_play_fixture_demo_menu() -> None:
    out = StringIO()
    inputs = iter(["2"])

    exit_code = play_project(
        ROOT / "fixtures",
        entry="DEMO_MENU",
        out=out,
        input_func=lambda _prompt: next(inputs),
    )

    text = out.getvalue()
    assert exit_code == 0
    assert "ERAplay demo" in text
    assert "2: 診察" in text
    assert "診察を選択しました。" in text
