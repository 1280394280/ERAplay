from pathlib import Path

from eraplay.ast import Label
from eraplay.project import load_project

ROOT = Path(__file__).resolve().parents[1]


def test_load_fixture_project() -> None:
    project = load_project(ROOT / "fixtures")

    assert len(project.erb_files) == 5
    assert len(project.erh_files) == 2
    assert len(project.csv_files) == 2

    labels = [
        node.name
        for loaded in project.erb_files
        for node in loaded.program.nodes
        if isinstance(node, Label)
    ]
    assert "EVENTFIRST" in labels
    assert "GREET" in labels

    dim_names = [
        dim.name
        for loaded in project.erh_files
        for dim in loaded.document.dims
    ]
    assert "MONEY" in dim_names

    csv_names = [loaded.file.path.name for loaded in project.csv_files]
    assert csv_names == ["Chara0000.csv", "GameBase.csv"]
