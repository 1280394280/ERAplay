from pathlib import Path

from eraplay.webpreview import create_preview_server, _runtime_state

ROOT = Path(__file__).resolve().parents[1]


def test_webpreview_initial_state_has_actions() -> None:
    server = create_preview_server(ROOT / "fixtures", entry="DEMO_MENU", port=0)
    try:
        state = _runtime_state(server.runtime)
    finally:
        server.server_close()

    assert state["waiting"] is True
    assert {"id": "1", "text": "通常業務"} in state["actions"]
    assert {"id": "2", "text": "診察"} in state["actions"]
