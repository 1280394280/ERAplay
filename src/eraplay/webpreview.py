from __future__ import annotations

import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from eraplay.project import load_project
from eraplay.runtime import MiniRuntime
from eraplay.translation import TranslationConfig, TranslationDisplayMode, translate_event_text
from eraplay.ui import OutputChannel, OutputKind


@dataclass
class PreviewSession:
    project_path: str | Path
    entry: str
    encoding: str | None = None
    runtime: MiniRuntime | None = None

    def start(self) -> MiniRuntime:
        project = load_project(self.project_path, preferred_encoding=self.encoding)
        runtime = MiniRuntime(project)
        runtime.run(self.entry)
        self.runtime = runtime
        return runtime

    def current(self) -> MiniRuntime:
        if self.runtime is None:
            return self.start()
        return self.runtime

    def restart(self) -> MiniRuntime:
        return self.start()


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
                self._send_json(_runtime_state(runtime, translation))
            else:
                self.send_error(404)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path not in ("/input", "/restart"):
                self.send_error(404)
                return
            if parsed.path == "/restart":
                runtime = session.restart()
                query = parse_qs(parsed.query)
                mode = query.get("mode", [None])[0]
                translation = _translation_with_mode(runtime.project.config.translation, mode)
                self._send_json(_runtime_state(runtime, translation))
                return
            length = int(self.headers.get("content-length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            data = parse_qs(body)
            value = data.get("value", [""])[0]
            runtime = session.current()
            runtime.console.clear()
            runtime.resume(_coerce_input(value))
            query = parse_qs(parsed.query)
            mode = query.get("mode", [None])[0]
            translation = _translation_with_mode(runtime.project.config.translation, mode)
            self._send_json(_runtime_state(runtime, translation))

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


def _runtime_state(runtime: MiniRuntime, translation=None) -> dict[str, object]:
    info: list[str] = []
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
    }


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
    #info { padding: 10px 14px; border-bottom: 1px solid #222; color: #c9f2ff; min-height: 22px; }
    main { display: grid; grid-template-columns: 1fr 320px; min-height: 0; }
    #main { padding: 14px; white-space: pre-wrap; line-height: 1.55; overflow: auto; }
    #history { padding: 14px; border-left: 1px solid #333; color: #888; overflow: auto; white-space: pre-wrap; }
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
      <aside id="history"></aside>
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
  </script>
</body>
</html>
"""
