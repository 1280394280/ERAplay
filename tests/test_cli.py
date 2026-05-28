from io import StringIO
from pathlib import Path

from eraplay.cli import check_project, main

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
