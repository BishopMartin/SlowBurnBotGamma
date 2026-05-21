import threading
import time
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

# Pending operator input (e.g., SMS verification code)
_pending_input_event: threading.Event = threading.Event()
_pending_input_prompt: str | None = None
_pending_input_value: str | None = None

# Kept for toggle_setting() / _get_setting_value()
_SETTINGS = [
    ("Pause sessions",    "_bot_paused"),
    ("Notifications",     "_notify_enabled"),
    ("Debug mode",        "bot_debug"),
    ("Browser only mode", "_browser_only"),
]

_browser_only: bool = False

_last_heartbeat_at: float = 0.0  # monotonic timestamp of last heartbeat send

_vnc_url: str = ""
_vnc_pin: str = ""

_NOTIFY_OPTIONS = ["none", "email", "sms", "both"]
_session_notify: str = "none"
_login_notify: str = "none"

# Status colour palette (used by burnBot_app.py)
COLOR = {
    "running":         "#adcc00",
    "initializing":    "#e5c07b",
    "waiting":         "#E5C07B",
    "paused":          "#E5C07B",
    "disabled":        "#cf3b0a",
    "system-disabled": "#cf3b0a",
    "no schedule":     "#cf3b0a",
    "max runs":        "#E5C07B",
    "idle":            "#9A968B",
    "off-schedule":    "#9A968B",
}
FG   = "#f4f3ee"   # titles / headers
TEXT = "#c9c7c0"   # regular body text
DIM  = "#9A968B"   # secondary / meta


# ---------------------------------------------------------------------------
# App bridge
# ---------------------------------------------------------------------------

def set_app(app) -> None:
    """Register the Textual app instance. Call flush_log_buffer() from on_mount to drain buffered lines."""
    global _app
    _app = app


def flush_log_buffer(app) -> None:
    """Flush lines buffered before the TUI started. Must be called from within the event loop (e.g. on_mount)."""
    with _lock:
        buffered = list(_log_buffer)
    for line in buffered:
        app._write_log(line)


# ---------------------------------------------------------------------------
# Core store update
# ---------------------------------------------------------------------------

def update(account_name: str, **kwargs) -> None:
    with _lock:
        _store.setdefault(account_name, {}).update(kwargs)
        full_state = dict(_store[account_name])
    if _app is not None:
        try:
            _app.call_from_thread(_app._update_account_row, account_name, full_state)
        except Exception:
            pass


def get_effective_max_runs(account_name: str):
    """Daily effective max runs (base + random offset) published by the scheduler.

    Returns None if the scheduler has not published one yet, in which case callers
    should fall back to the base max_runs_per_day from settings.
    """
    with _lock:
        return _store.get(account_name, {}).get("effective_max_runs")


def add_log(line: str) -> None:
    from rich.markup import escape
    line = escape(str(line))
    with _lock:
        _log_buffer.append(line)
    if _app is not None:
        _app.call_from_thread(_app._write_log, line)


# ---------------------------------------------------------------------------
# Public accessors / mutators
# ---------------------------------------------------------------------------

def get_pending_command():
    global _pending_command
    with _lock:
        cmd, _pending_command = _pending_command, None
        return cmd


def request_operator_input(prompt: str) -> str:
    """
    Block the calling (bot) thread until the operator submits input via the TUI.
    Returns the submitted string, or "" if cancelled or no TUI is available.
    """
    global _pending_input_prompt, _pending_input_value
    if _app is None:
        return ""
    with _lock:
        _pending_input_prompt = prompt
        _pending_input_value = None
        _pending_input_event.clear()
    _app.call_from_thread(_app._enter_input_prompt_mode, prompt)
    _pending_input_event.wait()
    with _lock:
        return _pending_input_value or ""


def deliver_operator_input(value: str) -> None:
    """Called from the UI thread to deliver the operator's submitted value to the waiting bot thread."""
    global _pending_input_value, _pending_input_prompt
    with _lock:
        _pending_input_value = value
        _pending_input_prompt = None
    _pending_input_event.set()


def get_pending_input_prompt() -> str | None:
    with _lock:
        return _pending_input_prompt


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


def cycle_notify(key: str) -> None:
    global _session_notify, _login_notify
    with _lock:
        if key == "_session_notify":
            _session_notify = _NOTIFY_OPTIONS[(_NOTIFY_OPTIONS.index(_session_notify) + 1) % len(_NOTIFY_OPTIONS)]
        elif key == "_login_notify":
            _login_notify = _NOTIFY_OPTIONS[(_NOTIFY_OPTIONS.index(_login_notify) + 1) % len(_NOTIFY_OPTIONS)]


def get_notify_value(key: str) -> str:
    if key == "_session_notify":
        return _session_notify
    if key == "_login_notify":
        return _login_notify
    return "none"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _toggle_setting_locked(idx: int) -> None:
    global _bot_paused, _notify_enabled, _browser_only
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
    elif key == "_browser_only":
        _browser_only = not _browser_only


def set_vnc_info(url: str = "", pin: str = "") -> None:
    global _vnc_url, _vnc_pin
    with _lock:
        _vnc_url = url or ""
        _vnc_pin = pin or ""


def get_vnc_info() -> tuple[str, str]:
    with _lock:
        return _vnc_url, _vnc_pin


def mark_heartbeat() -> None:
    global _last_heartbeat_at
    with _lock:
        _last_heartbeat_at = time.monotonic()


def seconds_since_heartbeat() -> int:
    with _lock:
        if _last_heartbeat_at == 0.0:
            return 0
        return int(time.monotonic() - _last_heartbeat_at)


def get_setting_value(key: str) -> bool:
    if key == "_bot_paused":
        return _bot_paused
    if key == "_notify_enabled":
        return _notify_enabled
    if key == "bot_debug":
        return CONFIG.getboolean('bot_settings', 'bot_debug', fallback=False)
    if key == "_browser_only":
        return _browser_only
    return False
