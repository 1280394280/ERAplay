from eraplay.csvdata import parse_csv_source


def test_parse_csv_rows() -> None:
    document = parse_csv_source(
        """
コード,ERAplayFixture
タイトル,ERAplay Fixture Game
;comment,ignored
"""
    )

    assert len(document.rows) == 2
    assert document.rows[0].key == "コード"
    assert document.rows[0].values == ("ERAplayFixture",)
    assert document.first_value_map()["タイトル"] == "ERAplay Fixture Game"
