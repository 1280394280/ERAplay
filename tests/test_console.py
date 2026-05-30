from eraplay.console import ClassicConsoleBuffer
from eraplay.ui import OutputChannel, OutputKind


def test_classic_console_print_and_line() -> None:
    console = ClassicConsoleBuffer()

    console.print("患者")
    console.print_line("请进")

    assert console.visible_text() == "患者请进"


def test_classic_console_clear_preserves_history() -> None:
    console = ClassicConsoleBuffer()

    console.print_line("old scene")
    console.clear()
    console.print_line("new scene")

    assert console.visible_text() == "new scene"
    assert console.history_text() == "old scene"


def test_classic_console_events_include_main_and_history() -> None:
    console = ClassicConsoleBuffer()

    console.print_line("old scene")
    console.clear()
    console.print_line("new scene")

    events = console.to_events()

    assert [event.channel for event in events] == [
        OutputChannel.MAIN,
        OutputChannel.HISTORY,
    ]
    assert [event.text for event in events] == ["new scene", "old scene"]


def test_classic_console_clear_lines_moves_removed_lines_to_history() -> None:
    console = ClassicConsoleBuffer()

    console.print_line("line 1")
    console.print_line("line 2")
    console.clear_lines(1)

    assert console.visible_text() == "line 1"
    assert console.history_text() == "line 2"


def test_classic_console_classifies_action_lines() -> None:
    console = ClassicConsoleBuffer()

    console.print_line("[95] 思考一下")

    events = console.to_events()

    assert events[0].channel is OutputChannel.ACTIONS
    assert events[0].kind is OutputKind.ACTION
    assert events[0].choice_id == "95"
    assert events[0].text == "思考一下"


def test_classic_console_classifies_multiple_actions_on_one_line() -> None:
    console = ClassicConsoleBuffer()

    console.print_line("[---] - －－－－－－－ [101] - 物色人才　　　　 [102] - 成人商店")

    events = console.to_events()

    assert [(event.choice_id, event.text) for event in events] == [
        ("101", "物色人才"),
        ("102", "成人商店"),
    ]
