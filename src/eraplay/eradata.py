from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from eraplay.csvdata import CsvDocument

NAME_TABLE_CSV = {
    "abl.csv": "ABLNAME",
    "base.csv": "BASENAME",
    "cstr.csv": "CSTRNAME",
    "exp.csv": "EXPNAME",
    "item.csv": "ITEMNAME",
    "mark.csv": "MARKNAME",
    "palam.csv": "PALAMNAME",
    "str.csv": "STRNAME",
    "talent.csv": "TALENTNAME",
    "train.csv": "TRAINNAME",
}


@dataclass(frozen=True)
class EraData:
    variable_sizes: dict[str, int] = field(default_factory=dict)
    name_tables: dict[str, dict[int, str]] = field(default_factory=dict)
    chara_files: tuple[Path, ...] = ()


@dataclass(frozen=True)
class LoadedCsvLike:
    path: Path
    document: CsvDocument


def build_era_data(root: Path, csv_files: tuple[LoadedCsvLike, ...]) -> EraData:
    variable_sizes: dict[str, int] = {}
    name_tables: dict[str, dict[int, str]] = {}
    chara_files: list[Path] = []

    for loaded in csv_files:
        name = loaded.path.name.casefold()
        if name == "variablesize.csv":
            variable_sizes.update(_parse_variable_sizes(loaded.document))
        if name in NAME_TABLE_CSV:
            name_tables[NAME_TABLE_CSV[name]] = _parse_name_table(loaded.document)
        if _is_chara_csv(root, loaded.path):
            chara_files.append(loaded.path)

    return EraData(
        variable_sizes=variable_sizes,
        name_tables=name_tables,
        chara_files=tuple(sorted(chara_files)),
    )


def _parse_variable_sizes(document: CsvDocument) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for row in document.rows:
        if not row.values:
            continue
        try:
            sizes[row.key.upper()] = int(row.values[0])
        except ValueError:
            continue
    return sizes


def _parse_name_table(document: CsvDocument) -> dict[int, str]:
    table: dict[int, str] = {}
    for row in document.rows:
        try:
            index = int(row.key)
        except ValueError:
            continue
        if row.values:
            table[index] = row.values[0]
    return table


def _is_chara_csv(root: Path, path: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = path.parts
    return len(parts) >= 2 and parts[-2].casefold() == "chara" and path.suffix.lower() == ".csv"
