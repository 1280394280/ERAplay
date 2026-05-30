from pathlib import Path

from eraplay.ast import Label
from eraplay.project import load_project

ROOT = Path(__file__).resolve().parents[1]


def test_load_fixture_project() -> None:
    project = load_project(ROOT / "fixtures")

    assert project.config.source_encoding == "utf-8"
    assert len(project.erb_files) == 6
    assert len(project.erh_files) == 2
    assert len(project.csv_files) == 2

    labels = [
        node.name
        for loaded in project.erb_files
        for node in loaded.program.nodes
        if isinstance(node, Label)
    ]
    assert "EVENTFIRST" in labels
    assert "DEMO_MENU" in labels
    assert "GREET" in labels

    dim_names = [
        dim.name
        for loaded in project.erh_files
        for dim in loaded.document.dims
    ]
    assert "MONEY" in dim_names

    csv_names = [loaded.file.path.name for loaded in project.csv_files]
    assert csv_names == ["Chara0000.csv", "GameBase.csv"]


def test_load_project_excludes_default_non_source_dirs(tmp_path: Path) -> None:
    (tmp_path / "ERB").mkdir()
    (tmp_path / "\u8cc7\u6599").mkdir()
    (tmp_path / "\u9644\u4ef6").mkdir()
    (tmp_path / "ERB" / "main.erb").write_text("@EVENTFIRST\n", encoding="utf-8")
    (tmp_path / "\u8cc7\u6599" / "template.erb").write_text("@EVENTFIRST\n", encoding="utf-8")
    (tmp_path / "\u9644\u4ef6" / "patch.erb").write_text("@EVENTFIRST\n", encoding="utf-8")

    project = load_project(tmp_path)

    assert [loaded.file.path.name for loaded in project.erb_files] == ["main.erb"]


def test_load_project_can_override_exclude_dirs(tmp_path: Path) -> None:
    (tmp_path / "eraplay.toml").write_text(
        '[project]\nsource_encoding = "utf-8"\nexclude_dirs = ["backup"]\n',
        encoding="utf-8",
    )
    (tmp_path / "ERB").mkdir()
    (tmp_path / "backup").mkdir()
    (tmp_path / "ERB" / "main.erb").write_text("@EVENTFIRST\n", encoding="utf-8")
    (tmp_path / "backup" / "old.erb").write_text("@OLD\n", encoding="utf-8")

    project = load_project(tmp_path)

    assert [loaded.file.path.name for loaded in project.erb_files] == ["main.erb"]


def test_load_project_builds_era_data(tmp_path: Path) -> None:
    (tmp_path / "CSV" / "Chara").mkdir(parents=True)
    (tmp_path / "CSV" / "VariableSize.CSV").write_text("FLAG,10000\n", encoding="utf-8")
    (tmp_path / "CSV" / "Abl.csv").write_text("0,Technique\n", encoding="utf-8")
    (tmp_path / "CSV" / "Chara" / "Chara0.csv").write_text("名前,Demo\n", encoding="utf-8")

    project = load_project(tmp_path)

    assert project.data.variable_sizes["FLAG"] == 10000
    assert project.data.name_tables["ABLNAME"] == {0: "Technique"}
    assert len(project.data.chara_files) == 1
