"""
Widget Server for PathwayViz.

Provides the WidgetServer class for managing embeddable real-time widgets.
"""

from __future__ import annotations

import json
import threading
import time
from typing import TYPE_CHECKING, Any

from ._pathwayviz import send_data as _send_data
from ._pathwayviz import start_server as _start_server
from ._pathwayviz import stop_server as _stop_server

if TYPE_CHECKING:
    from ._widgets import Widget


# Color palette for auto-assignment
COLORS = [
    "#00d4ff",  # cyan
    "#00ff88",  # green
    "#ff6b6b",  # red
    "#ffd93d",  # yellow
    "#c44dff",  # purple
    "#ff8c42",  # orange
    "#6bceff",  # light blue
    "#95e1a3",  # light green
]


class WidgetServer:
    """
    A server for hosting embeddable real-time widgets.

    Each widget is accessible at `/embed/{widget_id}` via iframe.

    Example:
        import pathway as pw
        import pathwayviz as pv

        orders = pw.io.kafka.read(...)
        revenue = orders.reduce(revenue=pw.reducers.sum(pw.this.amount))

        server = pv.WidgetServer(port=3000)
        server.register(pv.Stat(revenue, "revenue", id="revenue", title="Revenue"))
        server.start()
        pw.run()

    Then embed:
        <iframe src="http://localhost:3000/embed/revenue"></iframe>
    """

    def __init__(
        self,
        *,
        port: int = 3000,
        title: str = "PathwayViz",
        theme: str = "dark",
    ) -> None:
        """
        Create a new widget server.

        Args:
            port: Port to listen on (default: 3000)
            title: Server title (shown in browser tab)
            theme: Color theme ("dark" or "light")
        """
        self.port = port
        self.title = title
        self.theme = theme

        self._widgets: dict[str, dict] = {}
        self._layout: list[str] = []
        self._started = False
        self._color_index = 0
        self._lock = threading.Lock()

    def _next_color(self) -> str:
        """Get next color from palette."""
        color = COLORS[self._color_index % len(COLORS)]
        self._color_index += 1
        return color

    def register(self, widget: Widget) -> WidgetServer:
        """
        Register a widget with the server.

        Args:
            widget: Widget instance to register

        Returns:
            self (for chaining)

        Example:
            server.register(pv.Stat(data, "value", id="my_stat"))
        """
        with self._lock:
            widget_id = widget.id
            widget_config = widget._get_config()

            # Auto-assign color if not specified
            if "color" not in widget_config or widget_config.get("color") is None:
                widget_config["color"] = self._next_color()

            self._widgets[widget_id] = widget_config
            if widget_id not in self._layout:
                self._layout.append(widget_id)

            # Activate the widget's data subscription
            widget._activate(self)

            if self._started:
                self._broadcast_config()

        return self

    def _broadcast_config(self) -> None:
        """Broadcast widget configuration to all connected clients."""
        msg = {
            "type": "config",
            "title": self.title,
            "theme": self.theme,
            "widgets": self._widgets,
            "layout": self._layout,
            "embed_enabled": True,
        }
        _send_data(json.dumps(msg))

    def _config_broadcaster(self) -> None:
        """Periodically broadcast config to catch new connections."""
        while self._started:
            time.sleep(2.0)
            if self._widgets:
                self._broadcast_config()

    def start(self) -> None:
        """
        Start the widget server.

        After calling start(), widgets will begin streaming data.
        Call pw.run() after this to start the Pathway pipeline.

        Example:
            server.start()
            pw.run()
        """
        if self._started:
            return

        _start_server(self.port)
        self._started = True
        time.sleep(0.3)  # Let server start

        self._broadcast_config()

        # Background broadcaster for new connections
        t = threading.Thread(target=self._config_broadcaster, daemon=True)
        t.start()

        print(f"Widget server: http://localhost:{self.port}")
        print(f"Embed widgets: http://localhost:{self.port}/embed/{{widget_id}}")

    def stop(self) -> None:
        """Stop the widget server."""
        self._started = False
        _stop_server()

    @property
    def widgets(self) -> dict[str, dict]:
        """Get registered widget configurations."""
        return self._widgets.copy()

    def __enter__(self) -> WidgetServer:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - stops server."""
        self.stop()
