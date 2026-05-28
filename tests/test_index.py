from pathlib import Path

from eraplay.index import SymbolKind, build_project_index
from eraplay.project import load_project

ROOT = Path(__file__).resolve().parents[1]


def test_project_index_collects_labels() -> None:
    project = load_project(ROOT / "fixtures")
    index = build_project_index(project)

    labels = index.by_kind(SymbolKind.LABEL)
    assert {symbol.name for symbol in labels} >= {
        "EVENTFIRST",
        "CALC_SCORE",
        "GREET",
    }
    assert index.find("greet", SymbolKind.LABEL)[0].detail == "function"


def test_project_index_collects_erh_symbols() -> None:
    project = load_project(ROOT / "fixtures")
    index = build_project_index(project)

    assert index.find("DEFAULT_MONEY", SymbolKind.DEFINE)[0].detail == "30000"
    assert index.find("PLAYER_NAME", SymbolKind.VARIABLE)[0].detail == "string"
    assert index.find("RELATION", SymbolKind.VARIABLE)[0].detail == "integer[100]"


def test_project_index_collects_csv_keys() -> None:
    project = load_project(ROOT / "fixtures")
    index = build_project_index(project)

    title = index.find("タイトル", SymbolKind.CSV_KEY)[0]
    assert title.detail == "csv\\GameBase.csv"
    assert title.span.line == 3


def test_project_index_collects_assigned_variables() -> None:
    project = load_project(ROOT / "fixtures")
    index = build_project_index(project)

    variables = {symbol.name for symbol in index.by_kind(SymbolKind.VARIABLE)}
    assert {"FLAG", "LOCAL", "RESULT"} <= variables
