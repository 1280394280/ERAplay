from __future__ import annotations

import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from eraplay.compat import build_compatibility_report
from eraplay.index import SymbolKind, build_project_index
from eraplay.project import load_project
from eraplay.runtime import MiniRuntime, RuntimeError as EraRuntimeError
from eraplay.translation import TranslationConfig, TranslationDisplayMode, translate_event_text
from eraplay.ui import OutputChannel, OutputKind


@dataclass
class PreviewSession:
    project_path: str | Path
    entry: str
    encoding: str | None = None
    runtime: MiniRuntime | None = None
    log: list[str] | None = None
    error: str | None = None

    def start(self) -> MiniRuntime:
        project = load_project(self.project_path, preferred_encoding=self.encoding)
        runtime = MiniRuntime(project)
        self.runtime = runtime
        self.error = None
        self.log = []
        try:
            runtime.run(self.entry)
        except EraRuntimeError as error:
            self.error = str(error)
            self.add_log(f"start failed error={error}")
        else:
            self.add_log(f"started entry={self.entry}")
        return runtime

    def current(self) -> MiniRuntime:
        if self.runtime is None:
            return self.start()
        return self.runtime

    def restart(self) -> MiniRuntime:
        runtime = self.start()
        self.add_log("restarted")
        return runtime

    def switch_entry(self, entry: str) -> MiniRuntime:
        self.entry = entry
        runtime = self.start()
        self.add_log(f"entry switched entry={entry}")
        return runtime

    def add_log(self, message: str) -> None:
        if self.log is None:
            self.log = []
        self.log.append(message)


def serve_preview(
    path: str | Path,
    entry: str = "DEMO_MENU",
    host: str = "127.0.0.1",
    port: int = 8765,
    encoding: str | None = None,
) -> None:
    server = create_preview_server(path, entry=entry, host=host, port=port, encoding=encoding)
    print(f"ERAplay web preview: http://{host}:{server.server_port}")
    server.serve_forever()


def create_preview_server(
    path: str | Path,
    entry: str = "DEMO_MENU",
    host: str = "127.0.0.1",
    port: int = 8765,
    encoding: str | None = None,
) -> ThreadingHTTPServer:
    session = PreviewSession(path, entry, encoding)
    session.start()

    class PreviewHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_html(PAGE_HTML)
            elif parsed.path == "/state":
                query = parse_qs(parsed.query)
                mode = query.get("mode", [None])[0]
                runtime = session.current()
                translation = _translation_with_mode(runtime.project.config.translation, mode)
                self._send_json(
                    _runtime_state(
                        runtime,
                        translation,
                        _combined_log(session, runtime),
                        session.error,
                        session.entry,
                    )
                )
            elif parsed.path == "/compat":
                query = parse_qs(parsed.query)
                top = _query_int(query, "top", 5)
                runtime = session.current()
                self._send_json(_compat_state(runtime, top=top))
            elif parsed.path == "/entries":
                query = parse_qs(parsed.query)
                top = _query_int(query, "top", 20)
                runtime = session.current()
                self._send_json(_entry_state(runtime, top=top))
            else:
                self.send_error(404)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path not in ("/input", "/restart", "/entry"):
                self.send_error(404)
                return
            if parsed.path == "/entry":
                length = int(self.headers.get("content-length", "0"))
                body = self.rfile.read(length).decode("utf-8")
                entry = _body_value(body, self.headers.get("content-type", ""), "entry").strip()
                if not entry:
                    self.send_error(400, "missing entry")
                    return
                runtime = session.switch_entry(entry)
                query = parse_qs(parsed.query)
                mode = query.get("mode", [None])[0]
                translation = _translation_with_mode(runtime.project.config.translation, mode)
                self._send_json(
                    _runtime_state(
                        runtime,
                        translation,
                        _combined_log(session, runtime),
                        session.error,
                        session.entry,
                    )
                )
                return
            if parsed.path == "/restart":
                runtime = session.restart()
                query = parse_qs(parsed.query)
                mode = query.get("mode", [None])[0]
                translation = _translation_with_mode(runtime.project.config.translation, mode)
                self._send_json(
                    _runtime_state(
                        runtime,
                        translation,
                        _combined_log(session, runtime),
                        session.error,
                        session.entry,
                    )
                )
                return
            length = int(self.headers.get("content-length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            value = _body_value(body, self.headers.get("content-type", ""), "value")
            session.add_log(f"input value={value}")
            runtime = session.current()
            if session.error is None:
                runtime.console.clear()
                try:
                    runtime.resume(_coerce_input(value))
                except EraRuntimeError as error:
                    session.error = str(error)
                    session.add_log(f"input failed error={error}")
            query = parse_qs(parsed.query)
            mode = query.get("mode", [None])[0]
            translation = _translation_with_mode(runtime.project.config.translation, mode)
            self._send_json(
                _runtime_state(
                    runtime,
                    translation,
                    _combined_log(session, runtime),
                    session.error,
                    session.entry,
                )
            )

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_html(self, html: str) -> None:
            payload = html.encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_json(self, data: dict[str, object]) -> None:
            payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer((host, port), PreviewHandler)
    server.session = session  # type: ignore[attr-defined]
    server.runtime = session.current()  # type: ignore[attr-defined]
    return server


def _runtime_state(
    runtime: MiniRuntime,
    translation=None,
    event_log: list[str] | None = None,
    error: str | None = None,
    entry: str | None = None,
) -> dict[str, object]:
    info: list[str] = [_status_line(runtime)]
    if error is not None:
        info.append(f"error={error}")
    main: list[str] = []
    actions: list[dict[str, str]] = []
    history: list[str] = []
    for event in runtime.console.to_events():
        text = translate_event_text(event, translation) if translation is not None else event.text
        if event.channel is OutputChannel.ACTIONS and event.kind is OutputKind.ACTION:
            actions.append({"id": event.choice_id or "", "text": text})
        elif event.channel is OutputChannel.HISTORY:
            history.append(text)
        else:
            main.append(text)
    if not runtime.state.waiting_for_input:
        actions = []
    return {
        "info": info,
        "main": main,
        "actions": actions,
        "history": history,
        "waiting": runtime.state.waiting_for_input,
        "translation_mode": translation.display_mode.value if translation is not None else "original",
        "status": {
            "entry": entry,
            "waiting": runtime.state.waiting_for_input,
            "steps": runtime.state.steps,
            "result": runtime.state.result,
            "error": error,
        },
        "log": event_log or [],
    }


def _combined_log(session: PreviewSession, runtime: MiniRuntime) -> list[str]:
    return [*(session.log or []), *runtime.trace]


def _compat_state(runtime: MiniRuntime, top: int = 5) -> dict[str, object]:
    report = build_compatibility_report(runtime.project)
    return report.to_dict(top=top)


def _entry_state(runtime: MiniRuntime, top: int = 20) -> dict[str, object]:
    index = build_project_index(runtime.project)
    labels_by_name: dict[str, dict[str, object]] = {}
    for symbol in index.by_kind(SymbolKind.LABEL):
        score = _entry_score(symbol.name, symbol.detail)
        item = {
            "name": symbol.name,
            "detail": symbol.detail,
            "file": symbol.span.file,
            "line": symbol.span.line,
            "score": score,
        }
        key = symbol.name.upper()
        current = labels_by_name.get(key)
        if current is None or score > int(current["score"]):
            labels_by_name[key] = item
    labels = list(labels_by_name.values())
    labels.sort(key=lambda item: (-int(item["score"]), str(item["name"]).upper()))
    return {"entries": labels[:top], "count": len(labels)}


def _entry_score(name: str, detail: str) -> int:
    upper = name.upper()
    if upper == "__TITLE__":
        return 120
    if upper in {"EVENTFIRST", "SYSTEM_TITLE", "TITLE", "START"}:
        return 100
    if upper.startswith(("EVENT", "SYSTEM", "TITLE", "MAIN", "DEMO")):
        return 80
    if detail == "event":
        return 60
    return 10


def _translation_with_mode(
    config: TranslationConfig,
    mode: str | None,
) -> TranslationConfig:
    if mode is None:
        return config
    return TranslationConfig(
        enabled=config.enabled,
        source_language=config.source_language,
        target_language=config.target_language,
        provider=config.provider,
        endpoint=config.endpoint,
        model=config.model,
        api_key_env=config.api_key_env,
        cache=config.cache,
        display_mode=TranslationDisplayMode(mode),
        translate_channels=config.translate_channels,
    )


def _coerce_input(value: str) -> int | str:
    value = value.strip()
    if value.isdigit():
        return int(value)
    return value


def _input_value_from_body(body: str, content_type: str) -> str:
    return _body_value(body, content_type, "value")


def _body_value(body: str, content_type: str, key: str) -> str:
    if "application/json" in content_type:
        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            return ""
        value = payload.get(key, "") if isinstance(payload, dict) else ""
        return str(value)
    data = parse_qs(body)
    return data.get(key, [""])[0]


def _query_int(query: dict[str, list[str]], key: str, default: int) -> int:
    try:
        return int(query.get(key, [str(default)])[0])
    except ValueError:
        return default


def _status_line(runtime: MiniRuntime) -> str:
    waiting = "waiting" if runtime.state.waiting_for_input else "running"
    result = "" if runtime.state.result is None else str(runtime.state.result)
    return f"state={waiting} steps={runtime.state.steps} result={result}"


PAGE_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ERAplay Preview</title>
  <style>
    :root { color-scheme: dark; font-family: "Microsoft YaHei UI", "Yu Gothic UI", monospace; }
    body { margin: 0; background: #080808; color: #d8d8d8; }
    .layout { min-height: 100vh; display: grid; grid-template-rows: auto 1fr auto; }
    header { padding: 10px 14px; border-bottom: 1px solid #333; color: #89dceb; }
    header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .header-tools { display: inline-flex; align-items: center; gap: 10px; }
    .modes { display: inline-flex; gap: 6px; }
    .modes button { padding: 5px 8px; }
    .modes button.active { background: #39616c; }
    #info { padding: 10px 14px; border-bottom: 1px solid #222; color: #c9f2ff; min-height: 22px; font-size: 13px; }
    main { display: grid; grid-template-columns: 1fr 360px; min-height: 0; }
    #main { padding: 14px; white-space: pre-wrap; line-height: 1.55; overflow: auto; }
    aside { border-left: 1px solid #333; display: grid; grid-template-rows: 1fr 120px 120px 160px; min-height: 0; }
    #history { padding: 14px; color: #888; overflow: auto; white-space: pre-wrap; }
    #compat { padding: 10px 14px; border-top: 1px solid #333; color: #d5e5a3; overflow: auto; white-space: pre-wrap; font-size: 12px; }
    #entries { padding: 10px 14px; border-top: 1px solid #333; color: #f2c078; overflow: auto; white-space: pre-wrap; font-size: 12px; }
    #entries button { display: block; width: 100%; margin-top: 6px; padding: 5px 7px; text-align: left; font-size: 12px; }
    #log { padding: 10px 14px; border-top: 1px solid #333; color: #8ab4f8; overflow: auto; white-space: pre-wrap; font-size: 12px; }
    #actions { display: flex; gap: 8px; flex-wrap: wrap; padding: 12px; border-top: 1px solid #333; min-height: 44px; }
    button { background: #1b2a2f; color: #e8f8ff; border: 1px solid #39616c; padding: 8px 12px; border-radius: 6px; cursor: pointer; }
    button:hover { background: #24404a; }
  </style>
</head>
<body>
  <div class="layout">
    <header>
      <span>ERAplay Preview</span>
      <span class="header-tools">
        <button id="restart">Restart</button>
        <span class="modes">
          <button data-mode="original">Original</button>
          <button data-mode="translated">Translated</button>
          <button data-mode="bilingual">Bilingual</button>
        </span>
      </span>
    </header>
    <section id="info"></section>
    <main>
      <section id="main"></section>
      <aside>
        <section id="history"></section>
        <section id="compat"></section>
        <section id="entries"></section>
        <section id="log"></section>
      </aside>
    </main>
    <nav id="actions"></nav>
  </div>
  <script>
    let mode = 'bilingual';
    async function refresh() {
      const state = await fetch(`/state?mode=${encodeURIComponent(mode)}`).then(r => r.json());
      document.querySelector('#info').textContent = state.info.join('\\n');
      document.querySelector('#main').textContent = state.main.join('\\n');
      document.querySelector('#history').textContent = state.history.join('\\n');
      document.querySelector('#log').textContent = state.log.join('\\n');
      document.querySelectorAll('.modes button').forEach(button => {
        button.classList.toggle('active', button.dataset.mode === mode);
      });
      const actions = document.querySelector('#actions');
      actions.replaceChildren(...state.actions.map(action => {
        const button = document.createElement('button');
        button.textContent = `${action.id}: ${action.text}`;
        button.onclick = async () => {
          await fetch('/input', {
            method: 'POST',
            headers: {'content-type': 'application/x-www-form-urlencoded'},
            body: new URLSearchParams({value: action.id})
          });
          await refresh();
        };
        return button;
      }));
    }
    async function refreshCompat() {
      const report = await fetch('/compat?top=5').then(r => r.json());
      const calls = report.unresolved_calls.map(item => `${item.count}: ${item.target}`).join('\\n');
      const tables = Object.entries(report.data.name_tables).map(([name, count]) => `${name}:${count}`).join(' ');
      document.querySelector('#compat').textContent =
        `compat=${report.status} diagnostics=${report.diagnostics}` +
        `\\ndata vars=${report.data.variable_sizes} tables=${tables || 0} chara=${report.data.chara_files} gamebase=${report.data.game_base.loaded ? 'yes' : 'no'}` +
        (calls ? `\\n${calls}` : '');
    }
    async function refreshEntries() {
      const report = await fetch('/entries?top=6').then(r => r.json());
      const entries = document.querySelector('#entries');
      entries.replaceChildren(document.createTextNode(`entries=${report.count}\\n`), ...report.entries.map(item => {
        const button = document.createElement('button');
        button.textContent = item.name;
        button.title = `${item.detail} ${item.file}:${item.line}`;
        button.onclick = async () => {
          await fetch(`/entry?mode=${encodeURIComponent(mode)}`, {
            method: 'POST',
            headers: {'content-type': 'application/x-www-form-urlencoded'},
            body: new URLSearchParams({entry: item.name})
          });
          await refresh();
          await refreshEntries();
        };
        return button;
      }));
    }
    document.querySelectorAll('.modes button').forEach(button => {
      button.onclick = async () => {
        mode = button.dataset.mode;
        await refresh();
      };
    });
    document.querySelector('#restart').onclick = async () => {
      await fetch(`/restart?mode=${encodeURIComponent(mode)}`, {method: 'POST'});
      await refresh();
    };
    refresh();
    refreshCompat();
    refreshEntries();
  </script>
</body>
</html>
"""
