from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eraplay.ast import Program
from eraplay.config import ProjectConfig, load_project_config
from eraplay.csvdata import CsvDocument, parse_csv_source
from eraplay.erh import ErhDocument, parse_erh_source
from eraplay.parser import parse_source
from eraplay.text import DecodedText, read_text_file


@dataclass(frozen=True)
class LoadedTextFile:
    path: Path
    decoded: DecodedText


@dataclass(frozen=True)
class LoadedErb:
    file: LoadedTextFile
    program: Program


@dataclass(frozen=True)
class LoadedErh:
    file: LoadedTextFile
    document: ErhDocument


@dataclass(frozen=True)
class LoadedCsv:
    file: LoadedTextFile
    document: CsvDocument


@dataclass(frozen=True)
class EraProject:
    root: Path
    config: ProjectConfig
    erb_files: tuple[LoadedErb, ...]
    erh_files: tuple[LoadedErh, ...]
    csv_files: tuple[LoadedCsv, ...]


def load_project(
    root: str | Path,
    preferred_encoding: str | None = None,
) -> EraProject:
    root_path = Path(root)
    config = load_project_config(root_path)
    encoding = preferred_encoding or config.source_encoding
    erb_files = tuple(
        _load_erb(path, encoding) for path in _glob_case_insensitive(root_path, "*.erb")
    )
    erh_files = tuple(
        _load_erh(path, encoding) for path in _glob_case_insensitive(root_path, "*.erh")
    )
    csv_files = tuple(
        _load_csv(path, encoding) for path in _glob_case_insensitive(root_path, "*.csv")
    )
    return EraProject(root_path, config, erb_files, erh_files, csv_files)


def _load_text(path: Path, preferred_encoding: str | None) -> LoadedTextFile:
    return LoadedTextFile(path, read_text_file(path, preferred_encoding=preferred_encoding))


def _load_erb(path: Path, preferred_encoding: str | None) -> LoadedErb:
    loaded = _load_text(path, preferred_encoding)
    return LoadedErb(loaded, parse_source(loaded.decoded.text, str(path)))


def _load_erh(path: Path, preferred_encoding: str | None) -> LoadedErh:
    loaded = _load_text(path, preferred_encoding)
    return LoadedErh(loaded, parse_erh_source(loaded.decoded.text, str(path)))


def _load_csv(path: Path, preferred_encoding: str | None) -> LoadedCsv:
    loaded = _load_text(path, preferred_encoding)
    return LoadedCsv(loaded, parse_csv_source(loaded.decoded.text))


def _glob_case_insensitive(root: Path, pattern: str) -> list[Path]:
    suffix = pattern.removeprefix("*").lower()
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == suffix)
