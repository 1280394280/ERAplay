from pathlib import Path

from eraplay.csvdata import parse_csv_source
from eraplay.eradata import LoadedCsvLike, build_era_data


def test_build_era_data_reads_variable_sizes() -> None:
    root = Path("game")
    document = parse_csv_source("FLAG,10000\nITEM,1000\nBAD,not-number\n")

    data = build_era_data(root, (LoadedCsvLike(root / "CSV" / "VariableSize.CSV", document),))

    assert data.variable_sizes == {"FLAG": 10000, "ITEM": 1000}


def test_build_era_data_reads_name_tables() -> None:
    root = Path("game")
    document = parse_csv_source("0,Technique\n1,Knowledge\n")

    data = build_era_data(root, (LoadedCsvLike(root / "CSV" / "Abl.csv", document),))

    assert data.name_tables["ABLNAME"] == {0: "Technique", 1: "Knowledge"}


def test_build_era_data_reads_item_prices() -> None:
    root = Path("game")
    document = parse_csv_source("100,Demo,500\n101,Other,bad\n102,Third,700\n")

    data = build_era_data(root, (LoadedCsvLike(root / "CSV" / "Item.csv", document),))

    assert data.name_tables["ITEMNAME"] == {100: "Demo", 101: "Other", 102: "Third"}
    assert data.item_prices == {100: 500, 102: 700}


def test_build_era_data_counts_chara_files() -> None:
    root = Path("game")
    document = parse_csv_source("名前,Demo\n")

    data = build_era_data(
        root,
        (
            LoadedCsvLike(root / "CSV" / "Chara" / "Chara0.csv", document),
            LoadedCsvLike(root / "CSV" / "GameBase.csv", document),
        ),
    )

    assert data.chara_files == (root / "CSV" / "Chara" / "Chara0.csv",)


def test_build_era_data_reads_game_base_metadata() -> None:
    root = Path("game")
    document = parse_csv_source("タイトル,Demo,\nバージョン,1070\n作者,A,B\n")

    data = build_era_data(root, (LoadedCsvLike(root / "CSV" / "GameBase.csv", document),))

    assert data.game_base == {
        "タイトル": ("Demo",),
        "バージョン": ("1070",),
        "作者": ("A", "B"),
    }
