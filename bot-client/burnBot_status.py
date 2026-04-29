import threading
from collections import deque
from burnBot_config import CONFIG

_lock = threading.Lock()
_store: dict = {}       # account_name -> {status, next_run, last_action, run_info}
_app = None             # BurnBotApp instance; set via set_app() once TUI starts

_notify_enabled: bool = True
_bot_paused: bool = False
_stop_requested: bool = False
_pending_command = None     # str | None
_log_buffer: deque = deque(maxlen=300)

# Kept for toggle_setting() / _get_setting_value()
_SETTINGS = [
    ("Pause sessions", "_bot_paused"),
    ("Debug output",   "bot_debug"),
    ("Notifications",  "_notify_enabled"),
]

# Status colour palette (used by burnBot_app.py)
COLOR = {
    "running":         "#adcc00",
    "waiting":         "#E5C07B",
    "paused":          "#E5C07B",
    "disabled":        "#cf3b0a",
    "system-disabled": "#cf3b0a",
    "no schedule":     "#cf3b0a",
    "max runs":        "#E5C07B",
    "idle":            "#9A968B",
    "off-schedule":    "#9A968B",
}
FG  = "#f4f3ee"
DIM = "#9A968B"


# ---------------------------------------------------------------------------
# App bridge
# ---------------------------------------------------------------------------

def set_app(app) -> None:
    """Called once the Textual app is ready. Flushes buffered log lines."""
    global _app
    _app = app
    with _lock:
        buffered = list(_log_buffer)
    for line in buffered:
        app.call_from_thread(app._write_log, line)


# ---------------------------------------------------------------------------
# Core store update
# ---------------------------------------------------------------------------

def update(account_name: str, **kwargs) -> None:
    with _lock:
        _store.setdefault(account_name, {}).update(kwargs)
    if _app is not None:
        _app.call_from_thread(_app._update_account_row, account_name, dict(kwargs))


def add_log(line: str) -> None:
    with _lock:
        _log_buffer.append(str(line))
    if _app is not None:
        _app.call_from_thread(_app._write_log, str(line))


# ---------------------------------------------------------------------------
# Public accessors / mutators
# ---------------------------------------------------------------------------

def get_pending_command():
    global _pending_command
    with _lock:
        cmd, _pending_command = _pending_command, None
        return cmd


def is_notify_enabled() -> bool:
    with _lock:
        return _notify_enabled


def is_bot_paused() -> bool:
    with _lock:
        return _bot_paused


def set_bot_paused(val: bool) -> None:
    global _bot_paused
    with _lock:
        _bot_paused = val
    if _app is not None:
        _app.call_from_thread(_app._refresh_header)


def is_stop_requested() -> bool:
    with _lock:
        return _stop_requested


def set_stop_requested(val: bool) -> None:
    global _stop_requested
    with _lock:
        _stop_requested = val


def set_ui_mode(mode: str) -> None:
    """No-op in Textual world — retained for call-site compatibility."""
    pass


def toggle_setting(idx: int) -> None:
    with _lock:
        _toggle_setting_locked(idx)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _toggle_setting_locked(idx: int) -> None:
    global _bot_paused, _notify_enabled
    if idx < 0 or idx >= len(_SETTINGS):
        return
    _, key = _SETTINGS[idx]
    if key == "_bot_paused":
        _bot_paused = not _bot_paused
    elif key == "_notify_enabled":
        _notify_enabled = not _notify_enabled
    elif key == "bot_debug":
        cur = CONFIG.getboolean('bot_settings', 'bot_debug', fallback=False)
        CONFIG.set('bot_settings', 'bot_debug', str(not cur))


def get_setting_value(key: str) -> bool:
    if key == "_bot_paused":
        return _bot_paused
    if key == "_notify_enabled":
        return _notify_enabled
    if key == "bot_debug":
        return CONFIG.getboolean('bot_settings', 'bot_debug', fallback=False)
    return False
