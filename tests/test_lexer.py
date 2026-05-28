from eraplay.lexer import iter_logical_lines


def test_logical_lines_skip_blank_and_comments() -> None:
    lines = iter_logical_lines(
        """
        ; comment
        PRINTL "a;b"
        PRINTL c ; trailing comment
        """,
        "sample.erb",
    )

    assert [line.text for line in lines] == ['PRINTL "a;b"', "PRINTL c"]
    assert lines[0].span.line == 3
