from eraplay.erh import parse_erh_source


def test_parse_erh_define_and_dim() -> None:
    document = parse_erh_source(
        """
        #DEFINE DEFAULT_MONEY 30000
        #DIM MONEY
        #DIMS PLAYER_NAME
        #DIM RELATION, 100
        """,
        "test.erh",
    )

    assert document.defines[0].name == "DEFAULT_MONEY"
    assert document.defines[0].value == "30000"
    assert document.dims[0].name == "MONEY"
    assert document.dims[0].is_string is False
    assert document.dims[1].name == "PLAYER_NAME"
    assert document.dims[1].is_string is True
    assert document.dims[2].args == ("100",)
