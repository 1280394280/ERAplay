from io import StringIO
from pathlib import Path

from eraplay.cli import check_project, init_project, list_symbols, main

ROOT = Path(__file__).resolve().parents[1]


def test_check_project_reports_ok_for_fixtures() -> None:
    out = StringIO()

    exit_code = check_project(ROOT / "fixtures", out=out)

    assert exit_code == 0
    assert "OK:" in out.getvalue()
    assert "5 ERB" in out.getvalue()


def test_check_project_reports_diagnostics(tmp_path: Path) -> None:
    (tmp_path / "broken.erb").write_text("@EVENTFIRST\nCALL MISSING\n", encoding="utf-8")
    out = StringIO()

    exit_code = check_project(tmp_path, out=out)

    assert exit_code == 1
    assert "unresolved CALL target 'MISSING'" in out.getvalue()
    assert "1 diagnostic(s)" in out.getvalue()


def test_main_check_command() -> None:
    assert main(["check", str(ROOT / "fixtures")]) == 0


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
