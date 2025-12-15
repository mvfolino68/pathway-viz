"""
Dashboard state management.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Config:
    """Dashboard configuration."""

    title: str = "PathwayViz"
    theme: str = "dark"
    port: int = 3000
    embed_enabled: bool = False


@dataclass
class DashboardState:
    """Global dashboard state."""

    config: Config = field(default_factory=Config)
    widgets: dict[str, dict] = field(default_factory=dict)
    layout: list = field(default_factory=list)
    started: bool = False
    _color_index: int = 0
    _subscriptions: list = field(default_factory=list)


# Global singleton
_state = DashboardState()

# Color palette for widgets
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


def get_state() -> DashboardState:
    """Get the global dashboard state."""
    return _state


def reset_state() -> None:
    """Reset dashboard state (useful for testing)."""
    global _state
    _state = DashboardState()


def next_color() -> str:
    """Get next color from palette."""
    color = COLORS[_state._color_index % len(COLORS)]
    _state._color_index += 1
    return color
