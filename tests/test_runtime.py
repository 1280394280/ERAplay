from pathlib import Path

from eraplay.project import load_project
from eraplay.runtime import MiniRuntime, RuntimeError, run_project

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_prints_eventfirst_output() -> None:
    project = load_project(ROOT / "fixtures")

    result = run_project(project, "EVENTFIRST")

    assert "hello" in result.console.visible_text()


def test_runtime_calls_function_label(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
CALL GREET
PRINTL "done"

@GREET
PRINTL "hello"
RETURN 0
""",
        encoding="utf-8",
    )
    project = load_project(tmp_path)

    result = run_project(project)

    assert result.console.visible_text() == "hello\ndone"


def test_runtime_records_call_trace(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
CALL GREET

@GREET
RETURN 0
""",
        encoding="utf-8",
    )
    project = load_project(tmp_path)
    runtime = MiniRuntime(project)

    runtime.run()

    assert runtime.trace == ["call entry=EVENTFIRST", "call target=GREET"]


def test_runtime_records_ignored_command_trace(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text("@EVENTFIRST\nWAIT 10\nINPUT\n", encoding="utf-8")
    project = load_project(tmp_path)
    runtime = MiniRuntime(project)

    runtime.run()

    assert "ignored command=WAIT" in runtime.trace
    assert "input waiting" in runtime.trace


def test_runtime_assigns_simple_values(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
LOCAL = 10
LOCAL:1 = LOCAL + 1
""",
        encoding="utf-8",
    )
    project = load_project(tmp_path)
    runtime = MiniRuntime(project)

    runtime.run()

    assert runtime.state.variables["LOCAL"] == 10
    assert runtime.state.variables["LOCAL:1"] == 11


def test_runtime_executes_if_true_branch(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
FLAG:1 = 1
IF FLAG:1 > 0
PRINTL "on"
ELSE
PRINTL "off"
ENDIF
PRINTL "done"
""",
        encoding="utf-8",
    )
    project = load_project(tmp_path)

    result = run_project(project)

    assert result.console.visible_text() == "on\ndone"


def test_runtime_executes_else_branch(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
FLAG:1 = 0
IF FLAG:1 > 0
PRINTL "on"
ELSE
PRINTL "off"
ENDIF
""",
        encoding="utf-8",
    )
    project = load_project(tmp_path)

    result = run_project(project)

    assert result.console.visible_text() == "off"


def test_runtime_executes_nested_if(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
A = 1
B = 2
IF A > 0
IF B > 1
PRINTL "nested"
ENDIF
ELSE
PRINTL "wrong"
ENDIF
""",
        encoding="utf-8",
    )
    project = load_project(tmp_path)

    result = run_project(project)

    assert result.console.visible_text() == "nested"


def test_runtime_stops_at_input(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
PRINTL "[1] 通常業務"
INPUT
PRINTL "after input"
""",
        encoding="utf-8",
    )
    project = load_project(tmp_path)

    result = run_project(project)

    assert result.state.waiting_for_input is True
    assert result.console.visible_text() == "[1] 通常業務"


def test_runtime_input_output_can_be_classified_as_action(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
PRINTL "[95] 思考一下"
INPUT
""",
        encoding="utf-8",
    )
    project = load_project(tmp_path)

    result = run_project(project)
    events = result.console.to_events()

    assert events[0].channel.value == "actions"
    assert events[0].choice_id == "95"
    assert events[0].text == "思考一下"


def test_runtime_resumes_after_input(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
PRINTL "[1] 通常業務"
INPUT
PRINTL "after input"
""",
        encoding="utf-8",
    )
    project = load_project(tmp_path)
    runtime = MiniRuntime(project)

    runtime.run()
    result = runtime.resume(1)

    assert result.state.waiting_for_input is False
    assert result.state.variables["RESULT"] == 1
    assert result.console.visible_text() == "[1] 通常業務\nafter input"


def test_runtime_resumes_after_input_inside_call(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
CALL CHOOSE
PRINTL "returned"

@CHOOSE
PRINTL "[2] 診察"
INPUT
RETURN RESULT
""",
        encoding="utf-8",
    )
    project = load_project(tmp_path)
    runtime = MiniRuntime(project)

    runtime.run()
    result = runtime.resume(2)

    assert result.state.result == 2
    assert result.console.visible_text() == "[2] 診察\nreturned"


def test_runtime_goto_replaces_current_flow(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
PRINTL "before"
GOTO NEXT
PRINTL "skipped"

$NEXT
PRINTL "after"
""",
        encoding="utf-8",
    )
    project = load_project(tmp_path)

    result = run_project(project)

    assert result.console.visible_text() == "before\nafter"


def test_runtime_jump_aliases_goto(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
JUMP NEXT
PRINTL "skipped"

$NEXT
PRINTL "after"
""",
        encoding="utf-8",
    )
    project = load_project(tmp_path)

    result = run_project(project)

    assert result.console.visible_text() == "after"


def test_runtime_step_limit_stops_runaway_loop(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
GOTO EVENTFIRST
""",
        encoding="utf-8",
    )
    project = load_project(tmp_path)
    runtime = MiniRuntime(project, max_steps=5)

    try:
        runtime.run()
    except RuntimeError as error:
        assert "step limit exceeded" in str(error)
    else:
        raise AssertionError("expected RuntimeError")


def test_runtime_selectcase_matches_case(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
RESULT = 2
SELECTCASE RESULT
CASE 1
PRINTL "one"
CASE 2
PRINTL "two"
CASEELSE
PRINTL "else"
ENDSELECT
PRINTL "done"
""",
        encoding="utf-8",
    )
    project = load_project(tmp_path)

    result = run_project(project)

    assert result.console.visible_text() == "two\ndone"


def test_runtime_selectcase_uses_caseelse(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
RESULT = 9
SELECTCASE RESULT
CASE 1, 2
PRINTL "small"
CASEELSE
PRINTL "else"
ENDSELECT
""",
        encoding="utf-8",
    )
    project = load_project(tmp_path)

    result = run_project(project)

    assert result.console.visible_text() == "else"


def test_runtime_selectcase_matches_string_case(tmp_path: Path) -> None:
    (tmp_path / "main.erb").write_text(
        """
@EVENTFIRST
RESULT = "診察"
SELECTCASE RESULT
CASE "診察"
PRINTL "matched"
CASEELSE
PRINTL "else"
ENDSELECT
""",
        encoding="utf-8",
    )
    project = load_project(tmp_path)

    result = run_project(project)

    assert result.console.visible_text() == "matched"
