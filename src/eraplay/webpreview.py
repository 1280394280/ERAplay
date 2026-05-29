from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from eraplay.project import load_project
from eraplay.runtime import MiniRuntime
from eraplay.translation import translate_event_text
from eraplay.ui import OutputChannel, OutputKind


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
    project = load_project(path, preferred_encoding=encoding)
    runtime = MiniRuntime(project)
    runtime.run(entry)

    class PreviewHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_html(PAGE_HTML)
            elif parsed.path == "/state":
                self._send_json(_runtime_state(runtime, project.config.translation))
            else:
                self.send_error(404)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/input":
                self.send_error(404)
                return
            length = int(self.headers.get("content-length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            data = parse_qs(body)
            value = data.get("value", [""])[0]
            runtime.console.clear()
            runtime.resume(_coerce_input(value))
            self._send_json(_runtime_state(runtime, project.config.translation))

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
    server.runtime = runtime  # type: ignore[attr-defined]
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
    }


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
    <header>ERAplay Preview</header>
    <section id="info"></section>
    <main>
      <section id="main"></section>
      <aside id="history"></aside>
    </main>
    <nav id="actions"></nav>
  </div>
  <script>
    async function refresh() {
      const state = await fetch('/state').then(r => r.json());
      document.querySelector('#info').textContent = state.info.join('\\n');
      document.querySelector('#main').textContent = state.main.join('\\n');
      document.querySelector('#history').textContent = state.history.join('\\n');
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
    refresh();
  </script>
</body>
</html>
"""
