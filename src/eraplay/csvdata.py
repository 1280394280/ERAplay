from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO


@dataclass(frozen=True)
class CsvRow:
    key: str
    values: tuple[str, ...]
    line: int


@dataclass(frozen=True)
class CsvDocument:
    rows: tuple[CsvRow, ...]

    def first_value_map(self) -> dict[str, str]:
        return {row.key: row.values[0] for row in self.rows if row.values}


def parse_csv_source(source: str) -> CsvDocument:
    rows: list[CsvRow] = []
    reader = csv.reader(StringIO(source))
    for line_no, row in enumerate(reader, start=1):
        if not row:
            continue
        key = row[0].strip()
        if not key or key.startswith(";"):
            continue
        rows.append(CsvRow(key, tuple(cell.strip() for cell in row[1:]), line_no))
    return CsvDocument(tuple(rows))
