"""
Configuration API for PathwayViz dashboard.
"""

from __future__ import annotations

import json

from ._pathwayviz import send_data as _send_data
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


def configure(
    *,
    title: str | None = None,
    theme: str | None = None,
    port: int | None = None,
    embed: bool | None = None,
) -> None:
    """
    Configure the dashboard.

    Args:
        title: Dashboard title
        theme: Color theme ("dark" or "light")
        port: Server port (default: 3000)
        embed: Enable embeddable widget endpoints

    Example:
        pv.configure(title="Analytics", embed=True)
    """
    state = get_state()

    if title is not None:
        state.config.title = title
    if theme is not None:
        state.config.theme = theme
    if port is not None:
        state.config.port = port
    if embed is not None:
        state.config.embed_enabled = embed

    if state.started:
        _send_config()


def title(text: str) -> None:
    """Set dashboard title."""
    state = get_state()
    state.config.title = text
    if state.started:
        _send_config()
