from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TextIO

from eraplay.analysis import analyze_project
from eraplay.compat import build_compatibility_report
from eraplay.config import init_project_config
from eraplay.index import SymbolKind, build_project_index
from eraplay.project import load_project
from eraplay.reference_log import parse_emuera_log
from eraplay.runtime import MiniRuntime, run_project
from eraplay.ui import OutputChannel, OutputKind
from eraplay.webpreview import serve_preview


def main(argv: list[str] | None = None) -> int:
    _prefer_utf8_stdio()
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


def check_project(
    path: str | Path,
    encoding: str | None = None,
    out: TextIO | None = None,
    external_calls: tuple[str, ...] = (),
) -> int:
    if out is None:
        import sys

        out = sys.stdout

    project = load_project(path, preferred_encoding=encoding)
    index = build_project_index(project)
    diagnostics = analyze_project(project, index, external_calls=external_calls)

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


def compatibility_report(
    path: str | Path,
    encoding: str | None = None,
    out: TextIO | None = None,
    external_calls: tuple[str, ...] = (),
    top: int = 20,
    output_format: str = "text",
) -> int:
    if out is None:
        out = sys.stdout

    project = load_project(path, preferred_encoding=encoding)
    report = build_compatibility_report(project, external_calls=external_calls)
    if output_format == "json":
        print(
            json.dumps(report.to_dict(top=top, external_calls=external_calls), ensure_ascii=False),
            file=out,
        )
        return 0

    diagnostics = report.diagnostics
    print(f"Compatibility report: {project.root}", file=out)
    print(
        f"Files: {len(project.erb_files)} ERB, {len(project.erh_files)} ERH, "
        f"{len(project.csv_files)} CSV",
        file=out,
    )
    print(
        f"Data: {len(project.data.variable_sizes)} variable sizes, "
        f"{len(project.data.name_tables)} name tables, "
        f"{len(project.data.chara_files)} chara CSV",
        file=out,
    )
    print(f"Diagnostics: {len(diagnostics)}", file=out)
    if project.config.exclude_dirs:
        print(f"Excluded dirs: {', '.join(project.config.exclude_dirs)}", file=out)
    known_external = (*project.config.external_calls, *external_calls)
    if known_external:
        print(f"External calls: {', '.join(known_external)}", file=out)
    if not diagnostics:
        print("Status: OK", file=out)
        return 0

    print("[diagnostic kinds]", file=out)
    for kind, count in report.diagnostic_kinds.most_common():
        print(f"{count}: {kind}", file=out)

    unresolved_calls = report.unresolved_calls
    if unresolved_calls:
        print("[unresolved CALL targets]", file=out)
        for name, count in unresolved_calls.most_common(top):
            print(f"{count}: {name}", file=out)
    return 0


def init_project(
    path: str | Path,
    encoding: str = "utf-8",
    overwrite: bool = False,
    out: TextIO | None = None,
) -> int:
    if out is None:
        out = sys.stdout

    try:
        config_path = init_project_config(path, source_encoding=encoding, overwrite=overwrite)
    except FileExistsError as error:
        print(f"config already exists: {error.filename}", file=out)
        return 1

    print(f"created {config_path}", file=out)
    return 0


def summarize_emuera_log(
    path: str | Path,
    encoding: str | None = None,
    out: TextIO | None = None,
) -> int:
    if out is None:
        out = sys.stdout

    summary = parse_emuera_log(path, encoding=encoding)
    print(f"Emuera log: {summary.path}", file=out)
    print(f"Encoding: {summary.encoding}", file=out)
    print(
        f"Loaded: {len(summary.erb_files)} ERB, {len(summary.erh_files)} ERH, "
        f"{len(summary.csv_files)} CSV",
        file=out,
    )
    print(f"Chara CSV: {summary.chara_csv_count}", file=out)
    print(f"Warnings: {len(summary.warnings)}", file=out)
    if summary.non_comment_lines is not None:
        print(
            f"Script summary: {summary.non_comment_lines} non-comment lines, "
            f"{summary.function_count} functions, {summary.call_count} calls",
            file=out,
        )
    if summary.startup_screen:
        print("[startup screen]", file=out)
        for line in summary.startup_screen:
            print(line, file=out)
    return 0


def run_entry(
    path: str | Path,
    entry: str = "EVENTFIRST",
    encoding: str | None = None,
    out: TextIO | None = None,
) -> int:
    if out is None:
        out = sys.stdout

    project = load_project(path, preferred_encoding=encoding)
    result = run_project(project, entry)
    text = result.console.visible_text()
    if text:
        print(text, file=out)
    return 0


def play_project(
    path: str | Path,
    entry: str = "EVENTFIRST",
    encoding: str | None = None,
    out: TextIO | None = None,
    input_func=input,
) -> int:
    if out is None:
        out = sys.stdout

    project = load_project(path, preferred_encoding=encoding)
    runtime = MiniRuntime(project)
    runtime.run(entry)
    printed_line_count = 0

    while True:
        printed_line_count = _print_new_visible_lines(runtime, printed_line_count, out)
        if not runtime.state.waiting_for_input:
            return 0
        _print_actions(runtime, out)
        value = input_func("> ")
        runtime.resume(_coerce_input(value))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eraplay")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="load and diagnose an ERA project")
    check.add_argument("path", help="project directory to check")
    check.add_argument(
        "--encoding",
        help="preferred source encoding, for example utf-8, cp932, cp950, or cp936",
    )
    check.add_argument(
        "--external-call",
        action="append",
        default=[],
        help="treat a CALL target as provided externally",
    )
    check.set_defaults(
        handler=lambda args: check_project(
            args.path,
            args.encoding,
            external_calls=tuple(args.external_call),
        )
    )

    symbols = subparsers.add_parser("symbols", help="list indexed project symbols")
    symbols.add_argument("path", help="project directory to index")
    symbols.add_argument(
        "--encoding",
        help="preferred source encoding, for example utf-8, cp932, cp950, or cp936",
    )
    symbols.set_defaults(handler=lambda args: list_symbols(args.path, args.encoding))

    compat = subparsers.add_parser("compat", help="summarize ERA project compatibility gaps")
    compat.add_argument("path", help="project directory to inspect")
    compat.add_argument(
        "--encoding",
        help="preferred source encoding, for example utf-8, cp932, cp950, or cp936",
    )
    compat.add_argument(
        "--external-call",
        action="append",
        default=[],
        help="treat a CALL target as provided externally",
    )
    compat.add_argument(
        "--top",
        type=int,
        default=20,
        help="number of unresolved CALL targets to show",
    )
    compat.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="report output format",
    )
    compat.set_defaults(
        handler=lambda args: compatibility_report(
            args.path,
            args.encoding,
            external_calls=tuple(args.external_call),
            top=args.top,
            output_format=args.format,
        )
    )

    log = subparsers.add_parser("log", help="summarize an exported Emuera startup log")
    log.add_argument("path", help="Emuera log file to inspect")
    log.add_argument(
        "--encoding",
        help="preferred log encoding, usually utf-16 for Emuera logs",
    )
    log.set_defaults(handler=lambda args: summarize_emuera_log(args.path, args.encoding))

    init = subparsers.add_parser("init", help="create an eraplay.toml project config")
    init.add_argument("path", help="project directory to initialize")
    init.add_argument(
        "--encoding",
        default="utf-8",
        help="source encoding to write into eraplay.toml",
    )
    init.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing eraplay.toml",
    )
    init.set_defaults(handler=lambda args: init_project(args.path, args.encoding, args.force))

    run = subparsers.add_parser("run", help="run a minimal ERAplay entry label")
    run.add_argument("path", help="project directory to run")
    run.add_argument(
        "--entry",
        default="EVENTFIRST",
        help="entry label to run",
    )
    run.add_argument(
        "--encoding",
        help="preferred source encoding, for example utf-8, cp932, cp950, or cp936",
    )
    run.set_defaults(handler=lambda args: run_entry(args.path, args.entry, args.encoding))

    play = subparsers.add_parser("play", help="run interactively until the game exits")
    play.add_argument("path", help="project directory to play")
    play.add_argument(
        "--entry",
        default="EVENTFIRST",
        help="entry label to run",
    )
    play.add_argument(
        "--encoding",
        help="preferred source encoding, for example utf-8, cp932, cp950, or cp936",
    )
    play.set_defaults(handler=lambda args: play_project(args.path, args.entry, args.encoding))

    web = subparsers.add_parser("web", help="serve a minimal local web preview")
    web.add_argument("path", help="project directory to preview")
    web.add_argument("--entry", default="DEMO_MENU", help="entry label to run")
    web.add_argument("--host", default="127.0.0.1", help="host to bind")
    web.add_argument("--port", type=int, default=8765, help="port to bind")
    web.add_argument(
        "--encoding",
        help="preferred source encoding, for example utf-8, cp932, cp950, or cp936",
    )
    web.set_defaults(
        handler=lambda args: serve_preview(args.path, args.entry, args.host, args.port, args.encoding)
    )
    return parser


def _prefer_utf8_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def _print_new_visible_lines(runtime: MiniRuntime, printed_line_count: int, out: TextIO) -> int:
    lines = runtime.console.visible_text().splitlines()
    for line in lines[printed_line_count:]:
        print(line, file=out)
    return len(lines)


def _print_actions(runtime: MiniRuntime, out: TextIO) -> None:
    actions = [
        event
        for event in runtime.console.to_events()
        if event.channel is OutputChannel.ACTIONS and event.kind is OutputKind.ACTION
    ]
    if not actions:
        return
    print("[actions]", file=out)
    for action in actions:
        print(f"{action.choice_id}: {action.text}", file=out)


def _coerce_input(value: str) -> int | str:
    value = value.strip()
    if value.isdigit():
        return int(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
