from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from eraplay.text import read_text_file

_LOAD_SUFFIX = "\u8bfb\u53d6\u4e2d\u30fb\u30fb\u30fb"
_LOADED_MARKER = "\u8f7d\u5165\u5b8c\u6bd5"
_SUMMARY_RE = re.compile(r"^非注释行:(\d+), 函数数量:(\d+), 调用次数:(\d+)$")


@dataclass(frozen=True)
class EmueraLogSummary:
    path: Path
    encoding: str
    macro_loaded: bool
    csv_files: tuple[str, ...]
    erb_files: tuple[str, ...]
    erh_files: tuple[str, ...]
    warnings: tuple[str, ...]
    non_comment_lines: int | None
    function_count: int | None
    call_count: int | None
    startup_screen: tuple[str, ...]

    @property
    def chara_csv_count(self) -> int:
        return sum(1 for file in self.csv_files if file.replace("/", "\\").casefold().startswith("chara\\"))


def parse_emuera_log(path: str | Path, encoding: str | None = None) -> EmueraLogSummary:
    log_path = Path(path)
    decoded = read_text_file(log_path, preferred_encoding=encoding)
    lines = decoded.text.lstrip("\ufeff").splitlines()
    loaded_files = tuple(_loaded_file(line) for line in lines if _loaded_file(line) is not None)
    csv_files = tuple(file for file in loaded_files if file.casefold().endswith(".csv"))
    erb_files = tuple(file for file in loaded_files if file.casefold().endswith(".erb"))
    erh_files = tuple(file for file in loaded_files if file.casefold().endswith(".erh"))
    summary = _parse_script_summary(lines)

    return EmueraLogSummary(
        path=log_path,
        encoding=decoded.encoding,
        macro_loaded=any(line.startswith("加载macro.ini") for line in lines),
        csv_files=csv_files,
        erb_files=erb_files,
        erh_files=erh_files,
        warnings=tuple(line for line in lines if line.startswith("警告")),
        non_comment_lines=summary[0],
        function_count=summary[1],
        call_count=summary[2],
        startup_screen=_startup_screen(lines),
    )


def _loaded_file(line: str) -> str | None:
    if not line.endswith(_LOAD_SUFFIX):
        return None
    return line[: -len(_LOAD_SUFFIX)]


def _parse_script_summary(lines: list[str]) -> tuple[int | None, int | None, int | None]:
    for line in lines:
        match = _SUMMARY_RE.match(line)
        if match:
            return tuple(int(value) for value in match.groups())  # type: ignore[return-value]
    return None, None, None


def _startup_screen(lines: list[str]) -> tuple[str, ...]:
    try:
        loaded_index = lines.index(_LOADED_MARKER)
    except ValueError:
        return ()
    return tuple(lines[loaded_index + 1 :])
