from pathlib import Path

from eraplay.webpreview import create_preview_server, _runtime_state

ROOT = Path(__file__).resolve().parents[1]


def test_webpreview_initial_state_has_actions() -> None:
    server = create_preview_server(ROOT / "fixtures", entry="DEMO_MENU", port=0)
    try:
        state = _runtime_state(server.runtime, server.runtime.project.config.translation)
    finally:
        server.server_close()

    assert state["waiting"] is True
    assert {"id": "1", "text": "\u901a\u5e38\u696d\u52d9\n\u666e\u901a\u4e1a\u52a1"} in state["actions"]
    assert {"id": "2", "text": "\u8a3a\u5bdf\n\u8bca\u5bdf"} in state["actions"]


def test_webpreview_input_moves_previous_screen_to_history() -> None:
    server = create_preview_server(ROOT / "fixtures", entry="DEMO_MENU", port=0)
    runtime = server.runtime
    try:
        runtime.console.clear()
        runtime.resume(2)
        state = _runtime_state(runtime, runtime.project.config.translation)
    finally:
        server.server_close()

    assert state["waiting"] is False
    assert "\u8a3a\u5bdf\u3092\u9078\u629e\u3057\u307e\u3057\u305f\u3002\n\u5df2\u9009\u62e9\u8bca\u5bdf\u3002" in state["main"]
    assert "ERAplay demo\nERAplay \u6f14\u793a" in state["history"]
    assert "[2] \u8a3a\u5bdf\n[2] \u8bca\u5bdf" in state["history"]
