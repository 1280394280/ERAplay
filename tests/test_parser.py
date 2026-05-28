from eraplay.ast import Assignment, Call, Command, ElseBlock, EndIf, IfBlock, Label
from eraplay.parser import parse_source


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


def test_parse_function_label() -> None:
    program = parse_source("$CALC\nRETURN 1")

    assert isinstance(program.nodes[0], Label)
    assert program.nodes[0].name == "CALC"
    assert program.nodes[0].is_event is False
