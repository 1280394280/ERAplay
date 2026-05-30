from pathlib import Path

from eraplay.ast import (
    Assignment,
    Call,
    Case,
    CaseElse,
    Command,
    ElseBlock,
    ElseIfBlock,
    EndIf,
    EndSelect,
    Goto,
    IfBlock,
    Label,
    Return,
    SelectCase,
)
from eraplay.parser import parse_source

ROOT = Path(__file__).resolve().parents[1]


def test_parse_basic_erb_subset() -> None:
    program = parse_source(
        """
        @EVENTFIRST
        PRINTL "hello"
        FLAG:1 = 2
        IF FLAG:1 > 0
        CALL NEXT, 1, "x,y"
        ELSE
        PRINTL "bye"
        ENDIF
        """,
        "sample.erb",
    )

    assert len(program.nodes) == 8
    assert isinstance(program.nodes[0], Label)
    assert program.nodes[0].name == "EVENTFIRST"
    assert program.nodes[0].is_event is True

    assert isinstance(program.nodes[1], Command)
    assert program.nodes[1].name == "PRINTL"
    assert program.nodes[1].args == ('"hello"',)

    assert isinstance(program.nodes[2], Assignment)
    assert program.nodes[2].target == "FLAG:1"
    assert program.nodes[2].expression == "2"

    assert isinstance(program.nodes[3], IfBlock)
    assert program.nodes[3].condition == "FLAG:1 > 0"

    assert isinstance(program.nodes[4], Call)
    assert program.nodes[4].target == "NEXT"
    assert program.nodes[4].args == ("1", '"x,y"')

    assert isinstance(program.nodes[5], ElseBlock)
    assert isinstance(program.nodes[7], EndIf)


def test_parse_string_assignment_with_apostrophe_marker() -> None:
    program = parse_source("@EVENTFIRST\nCALLNAME:0 '= \"Demo\"\n")

    assert isinstance(program.nodes[1], Assignment)
    assert program.nodes[1].target == "CALLNAME:0"
    assert program.nodes[1].expression == '"Demo"'


def test_parse_dims_keeps_raw_declaration() -> None:
    program = parse_source('#DIMS TMP_LNAME,2 = "宫间","みやま"\n')

    assert isinstance(program.nodes[0], Command)
    assert program.nodes[0].name == "#DIMS"
    assert program.nodes[0].args == ('TMP_LNAME,2 = "宫间","みやま"',)


def test_parse_print_form_preserves_layout_spaces() -> None:
    program = parse_source("PRINTPLAINFORM     -    <hint>\n")

    assert isinstance(program.nodes[0], Command)
    assert program.nodes[0].name == "PRINTPLAINFORM"
    assert program.nodes[0].args == ("    -    <hint>",)


def test_parse_function_label() -> None:
    program = parse_source("@CALC\nRETURN 1")

    assert isinstance(program.nodes[0], Label)
    assert program.nodes[0].name == "CALC"
    assert program.nodes[0].is_event is False
    assert program.nodes[0].is_local is False
    assert isinstance(program.nodes[1], Return)
    assert program.nodes[1].expression == "1"


def test_parse_local_label() -> None:
    program = parse_source("$INPUT_LOOP\nPRINTL \"again\"")

    assert isinstance(program.nodes[0], Label)
    assert program.nodes[0].name == "INPUT_LOOP"
    assert program.nodes[0].is_local is True


def test_parse_label_args() -> None:
    program = parse_source("@MISSION_REPORT_59(ARG, LOCAL:1)\nRETURN 1")

    assert isinstance(program.nodes[0], Label)
    assert program.nodes[0].name == "MISSION_REPORT_59"
    assert program.nodes[0].args == ("ARG", "LOCAL:1")


def test_parse_all_erb_fixtures() -> None:
    for path in sorted((ROOT / "fixtures" / "erb").glob("*.erb")):
        source = path.read_text(encoding="utf-8")
        program = parse_source(source, str(path))
        assert program.nodes, path


def test_parse_call_fixture_keeps_target_and_args() -> None:
    path = ROOT / "fixtures" / "erb" / "call.erb"
    program = parse_source(path.read_text(encoding="utf-8"), str(path))
    calls = [node for node in program.nodes if isinstance(node, Call)]

    assert len(calls) == 1
    assert calls[0].target == "GREET"
    assert calls[0].args == ('"患者"', "1")


def test_parse_parenthesized_call_args() -> None:
    program = parse_source('CALL MISSION_LIST(1, LOCAL:1, "x,y")')
    call = program.nodes[0]

    assert isinstance(call, Call)
    assert call.target == "MISSION_LIST"
    assert call.args == ("1", "LOCAL:1", '"x,y"')


def test_parse_goto_and_jump() -> None:
    program = parse_source("@EVENTFIRST\nGOTO NEXT\nJUMP END")

    assert isinstance(program.nodes[1], Goto)
    assert program.nodes[1].target == "NEXT"
    assert isinstance(program.nodes[2], Goto)
    assert program.nodes[2].target == "END"


def test_parse_selectcase() -> None:
    program = parse_source(
        """
@EVENTFIRST
SELECTCASE RESULT
CASE 1, 2
PRINTL "matched"
CASEELSE
PRINTL "else"
ENDSELECT
""",
        "sample.erb",
    )

    assert isinstance(program.nodes[1], SelectCase)
    assert program.nodes[1].expression == "RESULT"
    assert isinstance(program.nodes[2], Case)
    assert program.nodes[2].values == ("1", "2")
    assert isinstance(program.nodes[4], CaseElse)
    assert isinstance(program.nodes[6], EndSelect)


def test_parse_elseif() -> None:
    program = parse_source(
        """
@EVENTFIRST
IF RESULT == 0
PRINTL "zero"
ELSEIF RESULT == 1
PRINTL "one"
ENDIF
"""
    )

    assert isinstance(program.nodes[3], ElseIfBlock)
    assert program.nodes[3].condition == "RESULT == 1"


def test_parse_compound_assignment_as_assignment() -> None:
    program = parse_source("TFLAG:100 += 1\nLOCAL -= 2")

    assert isinstance(program.nodes[0], Assignment)
    assert program.nodes[0].target == "TFLAG:100"
    assert program.nodes[0].expression == "TFLAG:100 + (1)"
    assert isinstance(program.nodes[1], Assignment)
    assert program.nodes[1].target == "LOCAL"
    assert program.nodes[1].expression == "LOCAL - (2)"
