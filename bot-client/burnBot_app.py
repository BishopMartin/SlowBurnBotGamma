# burnBot_app.py — Textual TUI for SlowBurnBot client

import os
import re
import threading
from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Input, RichLog, Static
from textual.containers import Horizontal, Vertical
from textual.color import Color
from textual.strip import Strip
from textual import on
from textual.events import Click
from rich.text import Text
from rich.segment import Segment
from rich.style import Style as RichStyle
from rich.color import Color as RichColor
from rich.markup import escape as _escape

import burnBot_theme as _theme


class DefaultBgRichLog(RichLog):
    """RichLog that renders the log pane with the terminal's default background.

    Textual's CSS ``background: transparent`` is not terminal-transparent: it
    blends with an internal black base color in the widget style pass. Applying
    ``bgcolor=default`` in ``render_line`` is too early because Textual applies
    the widget background *after* ``render_line``. Post-process ``render_lines``
    instead so Rich emits ANSI 49 (reset background) for every cell in the log
    pane after Textual has finished composing CSS styles.
    """

    DEFAULT_CSS = """
    DefaultBgRichLog {
        background: transparent;
        scrollbar-background: transparent;
        scrollbar-size-vertical: 0;
        color: $bb-dim;
        overflow-x: hidden;
        overflow-y: scroll;
    }
    """

    _DEFAULT_BG = RichStyle(bgcolor=RichColor.default())

    @classmethod
    def _strip_default_bg(cls, strip: Strip) -> Strip:
        segments = [
            Segment(text, style + cls._DEFAULT_BG if style else cls._DEFAULT_BG, control)
            for text, style, control in strip
        ]
        return Strip(segments, strip.cell_length)

    def render_lines(self, crop):
        return [self._strip_default_bg(strip) for strip in super().render_lines(crop)]

import burnBot_status as status_store
from burnBot_client_log import client_log_line


class CmdHint(Static):
    """A clickable command hint label in the input bar."""

    DEFAULT_CSS = """
    CmdHint {
        width: auto;
        background: $bb-surface;
        color: $bb-dim;
        content-align: right middle;
        padding: 0 1;
    }
    CmdHint:hover {
        color: $bb-accent;
    }
    """

    def __init__(self, cmd: str, **kwargs):
        super().__init__(cmd, **kwargs)
        self._cmd = cmd

    def on_click(self, event: Click) -> None:
        event.stop()
        app = self.app
        if hasattr(app, "_run_cmd"):
            app._run_cmd(self._cmd)
        try:
            app.query_one("#cmd-input", Input).focus()
        except Exception:
            pass


class BurnBotApp(App):

    CSS = """
    Screen {
        layers: base overlay;
        color: $bb-text;
        background: transparent;
    }

    #header-bar {
        height: 3;
        background: $bb-surface;
        color: $bb-heading;
        padding: 1 1 0 1;
        border: solid $bb-dim;
        border-top: none;
    }

    RichLog {
        border: none;
        color: $bb-dim;
        padding: 0;
    }
    #log {
        scrollbar-color: $bb-dim;
        scrollbar-background: transparent;
        scrollbar-size-vertical: 0;
        background: transparent !important;
        padding-left: 1;
    }

    #settings-overlay {
        display: none;
        background: $bb-surface;
        align: left top;
        padding: 1 0 0 1;
    }
    #settings-section-header {
        width: 50;
        background: $bb-surface;
        color: $bb-heading;
        padding: 0 0 0 1;
    }
    #settings-table {
        width: 50;
        height: auto;
        max-height: 10;
        border: solid $bb-dim;
    }
    #settings-hint {
        width: auto;
        background: $bb-surface;
        color: $bb-dim;
        margin-top: 0;
        padding: 0 0 0 1;
    }

    #tint-overlay {
        display: none;
        background: $bb-surface;
        align: left top;
        padding: 1 0 0 1;
    }
    #tint-section-header {
        width: 50;
        background: $bb-surface;
        color: $bb-heading;
        padding: 0 0 0 1;
    }
    #tint-table {
        width: 50;
        height: auto;
        max-height: 8;
        border: solid $bb-dim;
    }
    #tint-table > .datatable--cursor {
        background: $bb-surface-high;
        color: $bb-accent;
    }
    #tint-hint {
        width: auto;
        background: $bb-surface;
        color: $bb-dim;
        margin-top: 0;
        padding: 0 0 0 1;
    }

    #help-overlay {
        display: none;
        background: $bb-surface;
        align: left top;
        padding: 1 0 0 1;
    }
    #help-box {
        width: 62;
        height: auto;
        background: $bb-surface;
        border: solid $bb-dim;
        padding: 0 1;
    }
    #help-hint-inline {
        width: auto;
        background: $bb-surface;
        color: $bb-dim;
        margin-top: 0;
        padding: 0 0 0 1;
    }

    DataTable {
        height: auto;
        max-height: 16;
        background: $bb-surface;
        color: $bb-text;
        border: solid $bb-dim;
        border-bottom: none;
    }
    DataTable > .datatable--header {
        background: $bb-surface;
        color: $bb-heading;
        text-style: bold;
    }
    DataTable > .datatable--cursor {
        background: $bb-surface-high;
    }
    #settings-table > .datatable--cursor {
        background: $bb-surface-high;
        color: $bb-accent;
    }

    #vnc-bar {
        height: 2;
        background: $bb-surface;
        color: $bb-dim;
        padding: 0 1;
        border: solid $bb-dim;
        border-bottom: none;
        display: none;
    }

    #input-row {
        height: 3;
        background: $bb-surface;
        border: solid $bb-dim;
    }
    #input-row:focus-within {
        border: solid $bb-accent;
    }
    #input-prompt {
        width: 4;
        color: $bb-accent;
        background: $bb-surface;
        content-align: center middle;
    }
    #cmd-inner {
        width: 1fr;
        height: 1fr;
        background: $bb-surface;
    }
    Input {
        width: auto;
        min-width: 20;
        background: $bb-surface;
        color: $bb-heading;
        border: none;
        padding: 0 0 0 1;
    }
    Input:focus {
        border: none;
        background: $bb-surface;
        background-tint: transparent 0%;
    }
    Input > .input--cursor {
        background: $bb-accent;
        color: $bb-on-accent;
    }
    Input > .input--selection {
        background: $bb-accent 30%;
    }
    #cmd-ghost {
        width: 1fr;
        color: $bb-ghost;
        background: $bb-surface;
        content-align: left middle;
        padding: 0 0 0 1;
    }
    #input-hints {
        width: auto;
        background: $bb-surface;
        align: right middle;
    }
    #hint-exit {
        width: auto;
        background: $bb-surface;
        color: $bb-dim;
        content-align: right middle;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "clear_input", "Clear", show=False),
    ]

    _COMMANDS = ["/copy-log", "/exit", "/help", "/save-log", "/settings", "/start", "/stop", "/tint"]

    _HELP_CMDS = [
        ("/stop",     "Stop all sessions (bot stays running)"),
        ("/start",    "Resume sessions after /stop"),
        ("/exit",     "Fully exit the bot"),
        ("/settings", "Open settings panel"),
        ("/tint",     "Select color theme (tinty / terminal / default)"),
        ("/save-log", "Save a plain text copy of the log"),
        ("/copy-log", "Copy the log to the clipboard"),
        ("/help",     "Show this screen"),
        ("Esc",       "Return to main view"),
    ]

    def __init__(self, version: str, client_id: str, client_name: str,
                 bot_loop_fn, stop_flag):
        super().__init__()
        self._version        = version
        self._client_id      = client_id
        self._client_name    = client_name
        self._bot_loop_fn    = bot_loop_fn
        self._stop_flag      = stop_flag
        self._log_lines: list[str] = []
        self._completions: list[str] = []
        self._completion_idx: int = 0
        self._exact_match: str | None = None
        self._prompt_mode: bool = False
        self._cmd_history: list[str] = []
        self._history_pos: int = -1
        # Theme state — start with defaults; register() updates from config in on_mount
        self._tint_mode:   str  = "default"
        self._palette:     dict = _theme.DEFAULT_PALETTE
        self._css_palette: dict = _theme.DEFAULT_PALETTE

    # ------------------------------------------------------------------
    # CSS variables — called by Textual during CSS processing
    # ------------------------------------------------------------------

    def get_css_variables(self) -> dict[str, str]:
        base = super().get_css_variables()
        base.update(_theme.get_css_vars(self._css_palette))
        return base

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        p = self._palette
        yield Static("", id="header-bar")
        yield DefaultBgRichLog(highlight=False, markup=True, wrap=True, id="log")
        with Vertical(id="settings-overlay"):
            yield Static("Client Settings", id="settings-section-header")
            yield DataTable(id="settings-table", show_header=False, cursor_type="row")
            yield Static("", id="settings-hint")
        with Vertical(id="tint-overlay"):
            yield Static("Color Theme", id="tint-section-header")
            yield DataTable(id="tint-table", show_header=False, cursor_type="row")
            yield Static("", id="tint-hint")
        with Vertical(id="help-overlay"):
            with Vertical(id="help-box"):
                for cmd, desc in self._HELP_CMDS:
                    row = Text()
                    row.append(f"{cmd:<12}", style=p["accent"])
                    row.append(desc, style=p["dim"])
                    yield Static(row)
            yield Static("", id="help-hint-inline")
        yield DataTable(id="accounts", show_cursor=False)
        yield Static("", id="vnc-bar")
        with Horizontal(id="input-row"):
            with Horizontal(id="cmd-inner"):
                yield Input(placeholder="enter a command", id="cmd-input")
                yield Static("", id="cmd-ghost")
            with Horizontal(id="input-hints"):
                yield CmdHint("/stop", id="hint-toggle")
                yield Static("/exit", id="hint-exit")
                yield CmdHint("/settings", id="hint-settings")
                yield CmdHint("/tint", id="hint-tint")
                yield CmdHint("/help", id="hint-help")

    def on_mount(self) -> None:
        # 1. Add DataTable columns (before register so refresh methods can populate rows)
        accounts = self.query_one("#accounts", DataTable)
        accounts.add_column("Account",        key="account")
        accounts.add_column("Status",         key="status")
        accounts.add_column("Sessions Today", key="sessions_today")
        accounts.add_column("Next Run",       key="next_run")
        accounts.add_column("Last Run",       key="last_run")
        accounts.add_column("Last Action",    key="last_action", width=40)

        settings = self.query_one("#settings-table", DataTable)
        settings.add_columns("Setting", "Value")

        tint = self.query_one("#tint-table", DataTable)
        tint.add_columns("Mark", "Theme")

        # 2. Apply saved theme mode (reads config, updates palette, refreshes CSS + widgets)
        _theme.register(self)

        # 3. Add initial accounts placeholder row (self._palette now set)
        accounts.add_row(
            Text("no connected accounts", style=self._palette["dim"]),
            Text(""), Text(""), Text(""), Text(""), Text(""),
            key="_no_accounts",
        )

        # 4. Remaining setup
        log = self.query_one("#log", DefaultBgRichLog)
        log.styles.background = Color(0, 0, 0, a=0)
        log.styles.scrollbar_background = Color(0, 0, 0, a=0)

        self._refresh_header()
        self.set_interval(1.0, self._refresh_header)
        inp = self.query_one("#cmd-input", Input)
        inp.focus()
        self.call_after_refresh(self._deselect_input)
        self.call_after_refresh(self._update_ghost)
        status_store.flush_log_buffer(self)
        threading.Thread(target=self._bot_loop_fn, daemon=True).start()

    def _deselect_input(self) -> None:
        inp = self.query_one("#cmd-input", Input)
        inp.cursor_position = len(inp.value)

    def _enter_input_prompt_mode(self, prompt: str) -> None:
        """Switch the input bar to collect a free-text response (e.g., SMS code)."""
        self._prompt_mode = True
        inp = self.query_one("#cmd-input", Input)
        inp.placeholder = prompt
        inp.value = ""
        inp.focus()
        ghost = self.query_one("#cmd-ghost", Static)
        ghost.update(Text("↵ submit  Esc cancel", style=self._palette["accent"]))

    def _exit_input_prompt_mode(self) -> None:
        """Restore the input bar to normal command mode."""
        self._prompt_mode = False
        inp = self.query_one("#cmd-input", Input)
        inp.placeholder = "enter a command"
        inp.value = ""
        self._completions = []
        self._exact_match = None
        self._update_ghost()
        inp.focus()

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _refresh_header(self) -> None:
        p      = self._palette
        paused = status_store.is_bot_paused()
        now    = datetime.now().strftime("%I:%M %p")
        client_id_str = str(self._client_id).zfill(2)

        header = Text(no_wrap=True)
        header.append(f"SlowBurnBot Client v{self._version}", style=f"bold {p['brand']}")
        header.append(" | ", style=p["heading"])
        header.append(f"Client ID: {client_id_str}", style=p["heading"])
        if self._client_name:
            header.append(f" ({self._client_name})", style=p["heading"])
        header.append(" | ", style=p["heading"])
        header.append(now, style=p["heading"])
        header.append(" | Current State: ", style=p["heading"])
        if paused:
            header.append("[", style=p["heading"])
            header.append("STOPPED", style=f"bold {p['warn']}")
            header.append("]", style=p["heading"])
        else:
            header.append("[", style=p["heading"])
            header.append("ACTIVE", style=f"bold {p['accent']}")
            header.append("]", style=p["heading"])

        filled = status_store.seconds_since_heartbeat() % 15
        header.append(" |", style=p["heading"])
        header.append("█" * filled, style=p["text"])
        header.append("░" * (15 - filled), style=p["dim"])
        header.append("|", style=p["heading"])

        self.query_one("#header-bar", Static).update(header)

        vnc_url, vnc_pin = status_store.get_vnc_info()
        vnc_bar = self.query_one("#vnc-bar", Static)
        if vnc_url:
            bar = Text(no_wrap=True)
            bar.append("Remote View  ", style=p["heading"])
            bar.append(vnc_url, style=p["accent"])
            if vnc_pin:
                bar.append("   PIN: ", style=p["dim"])
                bar.append(vnc_pin, style=p["heading"])
            vnc_bar.update(bar)
            vnc_bar.display = True
        else:
            vnc_bar.display = False

        try:
            hint = self.query_one("#hint-toggle", CmdHint)
            hint_cmd = "/start" if paused else "/stop"
            hint._cmd = hint_cmd
            hint.update(hint_cmd)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Settings panel
    # ------------------------------------------------------------------

    def _open_settings(self) -> None:
        self.query_one("#help-overlay").display    = False
        self.query_one("#tint-overlay").display    = False
        self.query_one("#log").display             = False
        self.query_one("#settings-overlay").display = True
        self._refresh_settings_rows()
        self.query_one("#settings-table", DataTable).focus()

    def _close_settings(self) -> None:
        self.query_one("#settings-overlay").display = False
        self.query_one("#log").display = True
        self.query_one("#cmd-input", Input).focus()

    # (type, label, key)  type: header | separator | toggle | cycle
    _SETTINGS_ROWS = [
        ("header",    "Client Settings",            None),
        ("toggle",    "Debug mode",                 "bot_debug"),
        ("toggle",    "Browser only mode",          "_browser_only"),
        ("separator", "",                           None),
        ("header",    "Notification Settings",      None),
        ("cycle",     "Session Notifications",      "_session_notify"),
        ("cycle",     "Login/Error Notifications",  "_login_notify"),
    ]

    def _refresh_settings_rows(self) -> None:
        p = self._palette
        _actionable = {"toggle", "cycle"}
        table = self.query_one("#settings-table", DataTable)
        saved_row = table.cursor_row
        table.clear()
        for row_type, label, key in self._SETTINGS_ROWS:
            if row_type == "header":
                table.add_row(Text(label, style=f"bold {p['heading']}"), Text(""))
            elif row_type == "separator":
                table.add_row(Text(""), Text(""))
            elif row_type == "toggle":
                val = status_store.get_setting_value(key)
                val_text = Text("ON", style=p["accent"]) if val else Text("OFF", style=p["error"])
                table.add_row(Text(f"  {label}"), val_text)
            elif row_type == "cycle":
                val = status_store.get_notify_value(key)
                color = p["accent"] if val != "none" else p["dim"]
                table.add_row(Text(f"  {label}"), Text(val, style=color))
        # Land on an actionable row
        target = saved_row
        if target >= len(self._SETTINGS_ROWS) or self._SETTINGS_ROWS[target][0] not in _actionable:
            target = next(
                (i for i, (t, _, _k) in enumerate(self._SETTINGS_ROWS) if t in _actionable),
                saved_row,
            )
        table.move_cursor(row=target)

    def _activate_settings_row(self, row_idx: int) -> None:
        if row_idx < 0 or row_idx >= len(self._SETTINGS_ROWS):
            return
        row_type, _, key = self._SETTINGS_ROWS[row_idx]
        if row_type == "toggle":
            global_idx = next((i for i, (_, k) in enumerate(status_store._SETTINGS) if k == key), None)
            if global_idx is not None:
                status_store.toggle_setting(global_idx)
        elif row_type == "cycle":
            status_store.cycle_notify(key)
        self._refresh_settings_rows()

    # ------------------------------------------------------------------
    # Tint picker overlay
    # ------------------------------------------------------------------

    def _open_tint(self) -> None:
        self.query_one("#help-overlay").display     = False
        self.query_one("#settings-overlay").display = False
        self.query_one("#log").display              = False
        self.query_one("#tint-overlay").display     = True
        self._refresh_tint_rows()
        self.query_one("#tint-table", DataTable).focus()

    def _close_tint(self) -> None:
        self.query_one("#tint-overlay").display = False
        self.query_one("#log").display = True
        self.query_one("#cmd-input", Input).focus()

    def _refresh_tint_rows(self) -> None:
        p = self._palette
        table = self.query_one("#tint-table", DataTable)
        saved_row = table.cursor_row
        table.clear()
        current_mode = getattr(self, "_tint_mode", "default")
        for mode in _theme.MODES:
            label  = _theme.MODE_LABELS[mode]
            marker = Text("● ", style=p["accent"]) if current_mode == mode else Text("  ")
            table.add_row(marker, Text(label, style=p["text"]))
        table.move_cursor(row=min(saved_row, len(_theme.MODES) - 1))
        # Update the hint line
        try:
            self.query_one("#tint-hint", Static).update(
                f"[{p['dim']}]Enter/Tab: Apply   Esc: Back[/]"
            )
        except Exception:
            pass

    def _activate_tint_row(self, row_idx: int) -> None:
        modes = _theme.MODES
        if 0 <= row_idx < len(modes):
            _theme.apply_mode(self, modes[row_idx])

    # ------------------------------------------------------------------
    # Help panel
    # ------------------------------------------------------------------

    def _open_help(self) -> None:
        self.query_one("#settings-overlay").display = False
        self.query_one("#tint-overlay").display     = False
        self.query_one("#log").display              = False
        self.query_one("#help-overlay").display     = True

    def _close_help(self) -> None:
        self.query_one("#help-overlay").display = False
        self.query_one("#log").display = True
        self.query_one("#cmd-input", Input).focus()

    def _refresh_help_rows(self) -> None:
        """Re-render help box rows with current palette colors."""
        p = self._palette
        try:
            widgets = list(self.query("#help-box Static"))
            for widget, (cmd, desc) in zip(widgets, self._HELP_CMDS):
                row = Text()
                row.append(f"{cmd:<12}", style=p["accent"])
                row.append(desc, style=p["dim"])
                widget.update(row)
        except Exception:
            pass

    def _refresh_hint_widgets(self) -> None:
        """Re-render the markup hint lines in settings and help overlays."""
        p = self._palette
        try:
            self.query_one("#settings-hint", Static).update(
                f"[{p['dim']}]Enter or Tab: [/][{p['warn']}]Toggle[/]"
                f"[{p['dim']}]   Esc: [/][{p['warn']}]Back[/]"
            )
        except Exception:
            pass
        try:
            self.query_one("#help-hint-inline", Static).update(
                f"[{p['dim']}]Esc: [/][{p['warn']}]Close[/]"
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Log + accounts table (called from bot threads via call_from_thread)
    # ------------------------------------------------------------------

    def _write_log(self, line: str) -> None:
        self.query_one("#log", DefaultBgRichLog).write(line)
        try:
            plain = Text.from_markup(line).plain
        except Exception:
            plain = re.sub(r'\[/?[^\]]*\]', '', line)
        self._log_lines.append(plain)

    def _update_account_row(self, account_name: str, kwargs: dict) -> None:
        table  = self.query_one("#accounts", DataTable)
        try:
            table.remove_row("_no_accounts")
        except Exception:
            pass
        status = kwargs.get("status", "—")
        color  = _theme.status_color(self._palette, status)

        status_cell  = Text(status, style=color)
        run_info     = kwargs.get("run_info",    "—")
        next_run     = kwargs.get("next_run",    "—")
        last_run     = kwargs.get("last_run",    "—")
        last_action  = kwargs.get("last_action", "—")

        try:
            table.update_cell(account_name, "status",         status_cell,  update_width=False)
            table.update_cell(account_name, "sessions_today", run_info,     update_width=False)
            table.update_cell(account_name, "next_run",       next_run,     update_width=False)
            table.update_cell(account_name, "last_run",       last_run,     update_width=False)
            table.update_cell(account_name, "last_action",    last_action,  update_width=True)
        except Exception:
            try:
                table.add_row(
                    account_name, status_cell, run_info, next_run, last_run, last_action,
                    key=account_name,
                )
            except Exception:
                pass

    def _refresh_all_account_rows(self) -> None:
        """Re-render all account rows with the current palette's status colors."""
        for account_name, state in status_store.get_all_accounts().items():
            try:
                self._update_account_row(account_name, state)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Autocomplete ghost text
    # ------------------------------------------------------------------

    def _update_ghost(self) -> None:
        if self._prompt_mode:
            return
        p = self._palette
        ghost = self.query_one("#cmd-ghost", Static)
        if self._completions:
            current = self._completions[self._completion_idx]
            count   = len(self._completions)
            t = Text()
            t.append(current, style=p["accent"])
            if count > 1:
                t.append(f" [{self._completion_idx + 1}/{count}]↑↓ - tab to select", style=p["ghost"])
            else:
                t.append(" - tab to select", style=p["ghost"])
            ghost.update(t)
        elif self._exact_match:
            ghost.update(Text(self._exact_match, style=p["accent"]))
        else:
            ghost.update("")

    def on_click(self, event: Click) -> None:
        try:
            input_row = self.query_one("#input-row")
            if input_row.region.contains_point((event.screen_x, event.screen_y)):
                self.query_one("#cmd-input", Input).focus()
        except Exception:
            pass

    @on(Input.Changed, "#cmd-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        if self._prompt_mode:
            return
        _raw = event.value
        _clean = re.sub(r'[^\x20-\x7e]', '', _raw)
        _clean = re.sub(r'[\d;]+[Mm]', '', _clean)
        _clean = re.sub(r'\[[?<]?[\d;]*[A-Za-z]', '', _clean)
        if _clean != _raw:
            inp = self.query_one("#cmd-input", Input)
            inp.value = _clean
            inp.cursor_position = len(_clean)
            return
        typed = event.value
        if not typed:
            self._completions = []
            self._exact_match = None
            self._update_ghost()
            return
        if not typed.startswith("/"):
            inp = self.query_one("#cmd-input", Input)
            inp.value = "/" + typed
            inp.cursor_position = len(inp.value)
            return
        if len(typed) > 1:
            self._completions = [c for c in self._COMMANDS if c.startswith(typed) and c != typed]
            self._exact_match = typed if typed in self._COMMANDS else None
        else:
            self._completions = []
            self._exact_match = None
        self._completion_idx = 0
        self._update_ghost()

    def on_key(self, event) -> None:
        # Settings table navigation — skip non-actionable rows
        try:
            table = self.query_one("#settings-table", DataTable)
            if table.has_focus and self.query_one("#settings-overlay").display:
                _actionable = {"toggle", "cycle"}
                if event.key == "tab":
                    self._activate_settings_row(table.cursor_row)
                    event.prevent_default()
                    event.stop()
                    return
                if event.key in ("up", "down"):
                    step = -1 if event.key == "up" else 1
                    row = table.cursor_row
                    n = len(self._SETTINGS_ROWS)
                    for _ in range(n):
                        row = (row + step) % n
                        if self._SETTINGS_ROWS[row][0] in _actionable:
                            break
                    table.move_cursor(row=row)
                    event.prevent_default()
                    event.stop()
                    return
        except Exception:
            pass

        # Tint table navigation — all rows are actionable; Tab applies selection
        try:
            tint_table = self.query_one("#tint-table", DataTable)
            if tint_table.has_focus and self.query_one("#tint-overlay").display:
                if event.key == "tab":
                    self._activate_tint_row(tint_table.cursor_row)
                    event.prevent_default()
                    event.stop()
                    return
        except Exception:
            pass

        # Command input: autocomplete cycling, then history
        inp = self.query_one("#cmd-input", Input)
        if not inp.has_focus:
            return
        if self._completions:
            if event.key == "tab":
                inp.value = self._completions[self._completion_idx]
                inp.cursor_position = len(inp.value)
                self._exact_match = inp.value
                self._completions = []
                self._update_ghost()
                event.prevent_default()
                event.stop()
            elif event.key == "up":
                self._completion_idx = (self._completion_idx - 1) % len(self._completions)
                self._update_ghost()
                event.prevent_default()
                event.stop()
            elif event.key == "down":
                self._completion_idx = (self._completion_idx + 1) % len(self._completions)
                self._update_ghost()
                event.prevent_default()
                event.stop()
            return
        if event.key in ("up", "down"):
            event.stop()
            if self._prompt_mode or not self._cmd_history:
                return
            if event.key == "up":
                self._history_pos = min(self._history_pos + 1, len(self._cmd_history) - 1)
                inp.value = self._cmd_history[-(self._history_pos + 1)]
                inp.cursor_position = len(inp.value)
            else:
                if self._history_pos <= 0:
                    self._history_pos = -1
                    inp.value = "/"
                    inp.cursor_position = 1
                else:
                    self._history_pos -= 1
                    inp.value = self._cmd_history[-(self._history_pos + 1)]
                    inp.cursor_position = len(inp.value)

    # ------------------------------------------------------------------
    # Command input
    # ------------------------------------------------------------------

    def _run_cmd(self, cmd: str) -> None:
        """Execute a command string directly (used by clickable hints)."""
        self._dispatch_cmd(cmd.strip().lower())

    def _dispatch_cmd(self, cmd: str) -> None:
        if not cmd or cmd == "/":
            return
        if cmd == "/exit":
            self._stop_flag.set()
            status_store.set_stop_requested(True)
            self.exit()
        elif cmd == "/stop":
            status_store.set_bot_paused(True)
            self._write_log(_escape(client_log_line(None, "terminal-command", "Pausing bot execution")))
            self._refresh_header()
        elif cmd == "/start":
            status_store.set_bot_paused(False)
            self._write_log(_escape(client_log_line(None, "terminal-command", "Resuming bot execution")))
            self._refresh_header()
        elif cmd == "/settings":
            self._open_settings()
        elif cmd == "/tint":
            self._open_tint()
        elif cmd == "/help":
            self._open_help()
        elif cmd == "/save-log":
            ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"slowburnbot_log_{ts}.txt"
            try:
                with open(fname, "w", encoding="utf-8") as f:
                    f.write("\n".join(self._log_lines))
                self._write_log(_escape(client_log_line(None, "terminal-command", f"Log saved: {os.path.abspath(fname)}")))
            except Exception as e:
                self._write_log(_escape(client_log_line(None, "terminal-command", f"Save failed: {e}")))
        elif cmd == "/copy-log":
            try:
                self.copy_to_clipboard("\n".join(self._log_lines))
                self._write_log(_escape(client_log_line(None, "terminal-command", "Log copied to clipboard")))
            except Exception as e:
                self._write_log(_escape(client_log_line(None, "terminal-command", f"Copy failed: {e}")))
        else:
            self._write_log(_escape(client_log_line(None, "terminal-command", f"Unknown command '{cmd}' — type /help for list")))

    @on(Input.Submitted)
    def handle_command(self, event: Input.Submitted) -> None:
        if self._prompt_mode:
            value = event.value.strip()
            self._exit_input_prompt_mode()
            status_store.deliver_operator_input(value)
            return
        cmd = event.value.strip().lower()
        event.input.value = ""
        self._completions = []
        self._exact_match = None
        self._history_pos = -1
        self._update_ghost()
        if cmd and (not self._cmd_history or self._cmd_history[-1] != cmd):
            self._cmd_history.append(cmd)
        self._dispatch_cmd(cmd)

    @on(DataTable.RowSelected)
    def on_settings_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "settings-table":
            self._activate_settings_row(event.cursor_row)
        elif event.data_table.id == "tint-table":
            self._activate_tint_row(event.cursor_row)

    def action_clear_input(self) -> None:
        if self._prompt_mode:
            self._exit_input_prompt_mode()
            status_store.deliver_operator_input("")
            return
        inp = self.query_one("#cmd-input", Input)
        if inp.value:
            inp.value = ""
            self._completions = []
            self._exact_match = None
            self._update_ghost()
        elif self.query_one("#tint-overlay").display:
            self._close_tint()
        elif self.query_one("#help-overlay").display:
            self._close_help()
        elif self.query_one("#settings-overlay").display:
            self._close_settings()
