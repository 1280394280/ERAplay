from pathlib import Path

from eraplay.analysis import analyze_project
from eraplay.project import load_project

ROOT = Path(__file__).resolve().parents[1]


def test_fixture_project_has_no_diagnostics() -> None:
    project = load_project(ROOT / "fixtures")

    assert analyze_project(project) == ()


def test_unresolved_call_is_reported(tmp_path: Path) -> None:
    (tmp_path / "broken.erb").write_text("@EVENTFIRST\nCALL MISSING\n", encoding="utf-8")
    project = load_project(tmp_path)

    diagnostics = analyze_project(project)

    assert len(diagnostics) == 1
    assert diagnostics[0].message == "unresolved CALL target 'MISSING'"
    assert diagnostics[0].span.line == 2


def test_unresolved_goto_is_reported(tmp_path: Path) -> None:
    (tmp_path / "broken.erb").write_text("@EVENTFIRST\nGOTO MISSING\n", encoding="utf-8")
    project = load_project(tmp_path)

    diagnostics = analyze_project(project)

    assert len(diagnostics) == 1
    assert diagnostics[0].message == "unresolved GOTO/JUMP target 'MISSING'"
    assert diagnostics[0].span.line == 2


def test_duplicate_label_is_reported(tmp_path: Path) -> None:
    (tmp_path / "a.erb").write_text("@CALC\nRETURN 1\n", encoding="utf-8")
    (tmp_path / "b.erb").write_text("@CALC\nRETURN 2\n", encoding="utf-8")
    project = load_project(tmp_path)

    diagnostics = analyze_project(project)

    assert len(diagnostics) == 1
    assert diagnostics[0].message.startswith("duplicate label 'CALC'")
    assert diagnostics[0].span.file.endswith("b.erb")


def test_duplicate_local_label_is_allowed(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        "@A\n$INPUT_LOOP\nRETURN 1\n@B\n$INPUT_LOOP\nRETURN 2\n",
        encoding="utf-8",
    )
    project = load_project(tmp_path)

    assert analyze_project(project) == ()


def test_parenthesized_call_resolves_label(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        "@EVENTFIRST\nCALL CALC(1, LOCAL:1)\n@CALC\nRETURN 1\n",
        encoding="utf-8",
    )
    project = load_project(tmp_path)

    assert analyze_project(project) == ()


def test_duplicate_event_label_is_allowed_for_now(tmp_path: Path) -> None:
    (tmp_path / "a.erb").write_text("@EVENTFIRST\nPRINTL A\n", encoding="utf-8")
    (tmp_path / "b.erb").write_text("@EVENTFIRST\nPRINTL B\n", encoding="utf-8")
    project = load_project(tmp_path)

    assert analyze_project(project) == ()


def test_empty_erh_declaration_is_reported(tmp_path: Path) -> None:
    (tmp_path / "bad.erh").write_text("#DIM\n", encoding="utf-8")
    project = load_project(tmp_path)

    diagnostics = analyze_project(project)

    assert len(diagnostics) == 1
    assert diagnostics[0].message == "empty #DIM/#DIMS name"
