"""
Server control for PathwayViz.
"""

from __future__ import annotations

import json
import threading
import time

from ._pathway_viz import send_data as _send_data
from ._pathway_viz import start_server as _start_server
from ._pathway_viz import stop_server as _stop_server
from ._state import get_state


def _send_config() -> None:
    """Broadcast dashboard config to all clients."""
    state = get_state()
    msg = {
        "type": "config",
        "title": state.config.title,
        "theme": state.config.theme,
        "widgets": state.widgets,
        "layout": state.layout,
        "embed_enabled": state.config.embed_enabled,
    }
    _send_data(json.dumps(msg))


def _config_broadcaster() -> None:
    """Periodically broadcast config to catch new connections."""
    state = get_state()
    while state.started:
        time.sleep(2.0)
        if state.widgets:
            _send_config()


def start(port: int | None = None) -> None:
    """
    Start the PathwayViz server.

    Args:
        port: Port to listen on (default: 3000)

    After calling start(), data flows automatically from Pathway subscriptions.
    For manual widgets, use widget.send() to push data.

    Example:
        pv.table(my_pathway_table, title="Data")
        pv.start()
        pw.run()  # Pathway drives the data flow
    """
    state = get_state()

    if port is not None:
        state.config.port = port

    _start_server(state.config.port)
    state.started = True
    time.sleep(0.3)  # Let server start

    _send_config()

    # Background broadcaster
    t = threading.Thread(target=_config_broadcaster, daemon=True)
    t.start()

    dashboard_url = f"http://localhost:{state.config.port}"
    print(f"Dashboard: {dashboard_url}")

    if state.config.embed_enabled:
        print(f"Embed widgets: {dashboard_url}/embed/{{widget_id}}")


def stop() -> None:
    """Stop the PathwayViz server."""
    state = get_state()
    _stop_server()
    state.started = False
