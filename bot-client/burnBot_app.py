# burnBot_app.py — Textual TUI for SlowBurnBot client

import os
import re
import threading
from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Input, RichLog, Static
from textual.containers import Horizontal, Vertical
from textual import on
from rich.text import Text

import burnBot_status as status_store


class BurnBotApp(App):

    CSS = """
    Screen {
        background: #1a1a1a;
        layers: base overlay;
        color: #c9c7c0;
    }

    #header-bar {
        height: 2;
        margin-top: 1;
        background: #1a1a1a;
        color: #f4f3ee;
        padding: 0 1;
        border: solid #9A968B;
        border-top: none;
    }

    RichLog {
        border: none;
        background: #000000;
        color: #c9c7c0;
        padding: 0 0 0 1;
        scrollbar-color: #9A968B;
        scrollbar-background: #000000;
    }

    #settings-overlay {
        display: none;
        background: #1a1a1a;
        align: left top;
        padding: 1 0 0 1;
    }
    #settings-section-header {
        width: 50;
        color: #f4f3ee;
        padding: 0 0 0 1;
    }
    #settings-table {
        width: 50;
        height: auto;
        max-height: 10;
        border: solid #9A968B;
    }
    #settings-hint {
        width: auto;
        color: #9A968B;
        margin-top: 0;
        padding: 0 0 0 1;
    }

    #help-overlay {
        display: none;
        background: #1a1a1a;
        align: left top;
        padding: 1 0 0 1;
    }
    #help-box {
        width: 62;
        height: auto;
        border: solid #9A968B;
        padding: 0 1;
    }
    #help-hint-inline {
        width: auto;
        color: #9A968B;
        margin-top: 0;
        padding: 0 0 0 1;
    }

    DataTable {
        height: auto;
        max-height: 16;
        background: #1a1a1a;
        color: #c9c7c0;
        border: solid #9A968B;
        border-bottom: none;
    }
    DataTable > .datatable--header {
        background: #1a1a1a;
        color: #f4f3ee;
        text-style: bold;
    }
    DataTable > .datatable--cursor {
        background: #2a2a2a;
    }

    #input-row {
        height: 3;
        background: #1a1a1a;
        border: solid #9A968B;
    }
    #input-row:focus-within {
        border: solid #adcc00;
    }
    #input-prompt {
        width: 4;
        color: #adcc00;
        background: #1a1a1a;
        content-align: center middle;
    }
    #cmd-inner {
        width: 1fr;
        height: 1fr;
        background: #1a1a1a;
    }
    Input {
        width: auto;
        min-width: 20;
        background: #1a1a1a;
        color: #f4f3ee;
        border: none;
        padding: 0 0 0 1;
    }
    Input:focus {
        border: none;
    }
    #cmd-ghost {
        width: 1fr;
        color: #4a4a45;
        background: #1a1a1a;
        content-align: left middle;
        padding: 0 0 0 1;
    }
    #input-hints {
        width: auto;
        color: #9A968B;
        background: #1a1a1a;
        content-align: right middle;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "clear_input", "Clear", show=False),
    ]

    _COMMANDS = ["/exit", "/help", "/save-log", "/settings", "/start", "/stop"]

    _HELP_CMDS = [
        ("/stop",     "Stop all sessions (bot stays running)"),
        ("/start",    "Resume sessions after /stop"),
        ("/exit",     "Fully exit the bot"),
        ("/settings", "Open settings panel"),
        ("/save-log", "Save a plain text copy of the log"),
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

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Static("", id="header-bar")
        yield RichLog(highlight=False, markup=True, wrap=False, id="log")
        with Vertical(id="settings-overlay"):
            yield Static("Client Settings", id="settings-section-header")
            yield DataTable(id="settings-table", show_header=False, cursor_type="row")
            yield Static("[#9A968B]Enter or Tab: [/][#E5C07B]Toggle[/][#9A968B]   Esc: [/][#E5C07B]Back[/]", id="settings-hint")
        with Vertical(id="help-overlay"):
            with Vertical(id="help-box"):
                for cmd, desc in self._HELP_CMDS:
                    row = Text()
                    row.append(f"{cmd:<12}", style="#adcc00")
                    row.append(desc, style="#9A968B")
                    yield Static(row)
            yield Static("[#9A968B]Esc: [/][#E5C07B]Close[/]", id="help-hint-inline")
        yield DataTable(id="accounts", show_cursor=False)
        with Horizontal(id="input-row"):
            with Horizontal(id="cmd-inner"):
                yield Input(placeholder="", id="cmd-input")
                yield Static("", id="cmd-ghost")
            yield Static("", id="input-hints")

    def on_mount(self) -> None:
        accounts = self.query_one("#accounts", DataTable)
        accounts.add_column("Account",        key="account")
        accounts.add_column("Status",         key="status")
        accounts.add_column("Sessions Today", key="sessions_today")
        accounts.add_column("Next Run",       key="next_run")
        accounts.add_column("Last Action",    key="last_action", width=40)

        settings = self.query_one("#settings-table", DataTable)
        settings.add_columns("Setting", "Value")

        self._refresh_header()
        self.set_interval(1.0, self._refresh_header)
        inp = self.query_one("#cmd-input", Input)
        inp.value = "/"
        inp.focus()
        self.call_after_refresh(self._deselect_input)
        self.call_after_refresh(self._update_ghost)
        status_store.flush_log_buffer(self)
        threading.Thread(target=self._bot_loop_fn, daemon=True).start()

    def _deselect_input(self) -> None:
        inp = self.query_one("#cmd-input", Input)
        inp.cursor_position = len(inp.value)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _refresh_header(self) -> None:
        paused = status_store.is_bot_paused()
        now    = datetime.now().strftime("%I:%M %p")
        client_id_str = str(self._client_id).zfill(2)

        header = Text(no_wrap=True)
        header.append(f"SlowBurnBot Client v{self._version}", style=f"bold {status_store.FG}")
        header.append("  |  ", style=status_store.DIM)
        header.append(f"Client ID: {client_id_str}", style=status_store.DIM)
        if self._client_name:
            header.append(f" ({self._client_name})", style=status_store.DIM)
        header.append("  |  ", style=status_store.DIM)
        header.append(now, style=status_store.DIM)
        header.append("  |  Current State: ", style=status_store.DIM)
        if paused:
            header.append("[", style=status_store.DIM)
            header.append("STOPPED", style="bold #E5C07B")
            header.append("]", style=status_store.DIM)
        else:
            header.append("[", style=status_store.DIM)
            header.append("RUNNING", style="bold #adcc00")
            header.append("]", style=status_store.DIM)

        self.query_one("#header-bar", Static).update(header)

        try:
            hint_cmd = "/start" if paused else "/stop"
            self.query_one("#input-hints", Static).update(
                f"{hint_cmd}  /exit  /settings  /help"
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Settings panel (inline, replaces log area)
    # ------------------------------------------------------------------

    def _open_settings(self) -> None:
        self.query_one("#help-overlay").display = False
        self.query_one("#log").display = False
        self.query_one("#settings-overlay").display = True
        self._refresh_settings_rows()
        self.query_one("#settings-table", DataTable).focus()

    def _close_settings(self) -> None:
        self.query_one("#settings-overlay").display = False
        self.query_one("#log").display = True
        inp = self.query_one("#cmd-input", Input)
        inp.focus()
        if not inp.value:
            inp.value = "/"
            inp.cursor_position = 1

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
        table = self.query_one("#settings-table", DataTable)
        saved_row = table.cursor_row
        table.clear()
        for row_type, label, key in self._SETTINGS_ROWS:
            if row_type == "header":
                table.add_row(Text(label, style="bold #f4f3ee"), Text(""))
            elif row_type == "separator":
                table.add_row(Text(""), Text(""))
            elif row_type == "toggle":
                val = status_store.get_setting_value(key)
                val_text = Text("ON", style="#adcc00") if val else Text("OFF", style="#cf3b0a")
                table.add_row(Text(f"  {label}"), val_text)
            elif row_type == "cycle":
                val = status_store.get_notify_value(key)
                colors = {"none": "#9A968B", "email": "#adcc00", "sms": "#adcc00", "both": "#adcc00"}
                val_text = Text(val, style=colors.get(val, "#f4f3ee"))
                table.add_row(Text(f"  {label}"), val_text)
        if saved_row < len(self._SETTINGS_ROWS):
            table.move_cursor(row=saved_row)

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

    @on(DataTable.RowSelected)
    def on_settings_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "settings-table":
            self._activate_settings_row(event.cursor_row)

    # ------------------------------------------------------------------
    # Help panel (inline, replaces log area)
    # ------------------------------------------------------------------

    def _open_help(self) -> None:
        self.query_one("#settings-overlay").display = False
        self.query_one("#log").display = False
        self.query_one("#help-overlay").display = True

    def _close_help(self) -> None:
        self.query_one("#help-overlay").display = False
        self.query_one("#log").display = True
        inp = self.query_one("#cmd-input", Input)
        inp.focus()
        if not inp.value:
            inp.value = "/"
            inp.cursor_position = 1

    # ------------------------------------------------------------------
    # Log + accounts table (called from bot threads via call_from_thread)
    # ------------------------------------------------------------------

    def _write_log(self, line: str) -> None:
        self.query_one("#log", RichLog).write(line)
        try:
            plain = Text.from_markup(line).plain
        except Exception:
            plain = re.sub(r'\[/?[^\]]*\]', '', line)
        self._log_lines.append(plain)

    def _update_account_row(self, account_name: str, kwargs: dict) -> None:
        table  = self.query_one("#accounts", DataTable)
        status = kwargs.get("status", "—")
        color  = status_store.COLOR.get(status, status_store.DIM)

        status_cell  = Text(status, style=color)
        run_info     = kwargs.get("run_info",    "—")
        next_run     = kwargs.get("next_run",    "—")
        last_action  = kwargs.get("last_action", "—")

        try:
            table.update_cell(account_name, "status",         status_cell,  update_width=False)
            table.update_cell(account_name, "sessions_today", run_info,     update_width=False)
            table.update_cell(account_name, "next_run",       next_run,     update_width=False)
            table.update_cell(account_name, "last_action",    last_action,  update_width=True)
        except Exception:
            try:
                table.add_row(
                    account_name, status_cell, run_info, next_run, last_action,
                    key=account_name,
                )
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Autocomplete ghost text
    # ------------------------------------------------------------------

    def _update_ghost(self) -> None:
        ghost = self.query_one("#cmd-ghost", Static)
        if self._completions:
            current = self._completions[self._completion_idx]
            count   = len(self._completions)
            t = Text()
            t.append(current, style="#adcc00")
            if count > 1:
                t.append(f" [{self._completion_idx + 1}/{count}]↑↓ - tab to select", style="#4a4a45")
            else:
                t.append(" - tab to select", style="#4a4a45")
            ghost.update(t)
        else:
            try:
                inp = self.query_one("#cmd-input", Input)
                if inp.value == "/":
                    ghost.update(Text("enter a command", style="#4a4a45"))
                    return
            except Exception:
                pass
            ghost.update("")

    @on(Input.Changed, "#cmd-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        typed = event.value
        if not typed:
            self._completions = []
            self._update_ghost()
            inp = self.query_one("#cmd-input", Input)
            inp.value = "/"
            inp.cursor_position = 1
            return
        if typed.startswith("/") and len(typed) > 1:
            self._completions = [c for c in self._COMMANDS if c.startswith(typed) and c != typed]
        else:
            self._completions = []
        self._completion_idx = 0
        self._update_ghost()

    def on_key(self, event) -> None:
        # Tab toggle in settings table
        if event.key == "tab":
            try:
                table = self.query_one("#settings-table", DataTable)
                if table.has_focus and self.query_one("#settings-overlay").display:
                    self._activate_settings_row(table.cursor_row)
                    event.prevent_default()
                    event.stop()
                    return
            except Exception:
                pass

        # Autocomplete in command input
        inp = self.query_one("#cmd-input", Input)
        if not inp.has_focus or not self._completions:
            return
        if event.key == "tab":
            inp.value = self._completions[self._completion_idx]
            inp.cursor_position = len(inp.value)
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

    # ------------------------------------------------------------------
    # Command input
    # ------------------------------------------------------------------

    @on(Input.Submitted)
    def handle_command(self, event: Input.Submitted) -> None:
        cmd = event.value.strip().lower()
        event.input.value = "/"
        event.input.cursor_position = 1
        self._completions = []
        self._update_ghost()
        if not cmd or cmd == "/":
            return
        if cmd == "/exit":
            self._stop_flag.set()
            status_store.set_stop_requested(True)
            self.exit()
        elif cmd == "/stop":
            status_store.set_bot_paused(True)
            self._write_log(f"[{status_store.DIM}][[bot]][[user command]][/] - Pausing bot execution")
            self._refresh_header()
        elif cmd == "/start":
            status_store.set_bot_paused(False)
            self._write_log(f"[{status_store.DIM}][[bot]][[user command]][/] - Resuming bot execution")
            self._refresh_header()
        elif cmd == "/settings":
            self._open_settings()
        elif cmd == "/help":
            self._open_help()
        elif cmd == "/save-log":
            ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"slowburnbot_log_{ts}.txt"
            try:
                with open(fname, "w", encoding="utf-8") as f:
                    f.write("\n".join(self._log_lines))
                self._write_log(f"[{status_store.DIM}][[bot]][[user command]][/] - Log saved → {os.path.abspath(fname)}")
            except Exception as e:
                self._write_log(f"[{status_store.DIM}][[bot]][[user command]][/] - Save failed: {e}")
        else:
            self._write_log(f"[{status_store.DIM}][[bot]][[user command]][/] - Unknown command '{cmd}' — type /help for list")

    def action_clear_input(self) -> None:
        inp = self.query_one("#cmd-input", Input)
        if inp.value and inp.value != "/":
            inp.value = "/"
            inp.cursor_position = 1
            self._completions = []
            self._update_ghost()
        elif self.query_one("#help-overlay").display:
            self._close_help()
        elif self.query_one("#settings-overlay").display:
            self._close_settings()
