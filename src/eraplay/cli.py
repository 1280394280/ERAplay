from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from eraplay.analysis import analyze_project
from eraplay.index import SymbolKind, build_project_index
from eraplay.project import load_project


def main(argv: list[str] | None = None) -> int:
    _prefer_utf8_stdio()
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


def check_project(path: str | Path, encoding: str | None = None, out: TextIO | None = None) -> int:
    if out is None:
        import sys

        out = sys.stdout

    project = load_project(path, preferred_encoding=encoding)
    index = build_project_index(project)
    diagnostics = analyze_project(project, index)

    if not diagnostics:
        print(
            f"OK: {project.root} "
            f"({len(project.erb_files)} ERB, {len(project.erh_files)} ERH, {len(project.csv_files)} CSV)",
            file=out,
        )
        return 0

    for diagnostic in diagnostics:
        span = diagnostic.span
        print(
            f"{span.file}:{span.line}:{span.column}: "
            f"{diagnostic.severity}: {diagnostic.message}",
            file=out,
        )
    print(f"{len(diagnostics)} diagnostic(s)", file=out)
    return 1


def list_symbols(path: str | Path, encoding: str | None = None, out: TextIO | None = None) -> int:
    if out is None:
        import sys

        out = sys.stdout

    project = load_project(path, preferred_encoding=encoding)
    index = build_project_index(project)
    for kind in SymbolKind:
        symbols = index.by_kind(kind)
        if not symbols:
            continue
        print(f"[{kind.value}]", file=out)
        for symbol in symbols:
            detail = f" ({symbol.detail})" if symbol.detail else ""
            print(
                f"{symbol.name}{detail} - {symbol.span.file}:{symbol.span.line}",
                file=out,
            )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eraplay")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="load and diagnose an ERA project")
    check.add_argument("path", help="project directory to check")
    check.add_argument(
        "--encoding",
        help="preferred source encoding, for example utf-8, cp932, cp950, or cp936",
    )
    check.set_defaults(handler=lambda args: check_project(args.path, args.encoding))

    symbols = subparsers.add_parser("symbols", help="list indexed project symbols")
    symbols.add_argument("path", help="project directory to index")
    symbols.add_argument(
        "--encoding",
        help="preferred source encoding, for example utf-8, cp932, cp950, or cp936",
    )
    symbols.set_defaults(handler=lambda args: list_symbols(args.path, args.encoding))
    return parser


def _prefer_utf8_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
