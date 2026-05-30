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

    assert [(event.choice_id, event.text, event.enabled) for event in events] == [
        ("---", "－－－－－－－", False),
        ("101", "物色人才", True),
        ("102", "成人商店", True),
    ]


def test_classic_console_stops_action_text_at_any_next_bracket() -> None:
    console = ClassicConsoleBuffer()

    console.print_line("[109] - Visit [---] - -----")

    events = console.to_events()

    assert [(event.choice_id, event.text, event.enabled) for event in events] == [
        ("109", "Visit", True),
        ("---", "-----", False),
    ]


def test_classic_console_classifies_disabled_choice_placeholders() -> None:
    console = ClassicConsoleBuffer()

    console.print_line("[---] - Locked [999]Return")

    events = console.to_events()

    assert [(event.choice_id, event.text, event.enabled) for event in events] == [
        ("---", "Locked", False),
        ("999", "Return", True),
    ]


def test_classic_console_keeps_non_choice_brackets_in_main_text() -> None:
    console = ClassicConsoleBuffer()

    console.print_line("[春] 4月 第1周")

    events = console.to_events()

    assert events[0].channel is OutputChannel.MAIN
    assert events[0].text == "[春] 4月 第1周"


def test_classic_console_keeps_status_brackets_inside_action_text() -> None:
    console = ClassicConsoleBuffer()

    console.print_line("[1] Hero | < > [Type] [999]Return")

    events = console.to_events()

    assert [(event.choice_id, event.text) for event in events] == [
        ("1", "Hero | < > [Type]"),
        ("999", "Return"),
    ]
