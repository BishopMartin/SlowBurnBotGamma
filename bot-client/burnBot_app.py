# burnBot_app.py — Textual TUI for SlowBurnBot client

import os
import re
import threading
from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Input, RichLog, Static
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual import on
from rich.text import Text

import burnBot_status as status_store


# ---------------------------------------------------------------------------
# Help overlay screen
# ---------------------------------------------------------------------------

class HelpScreen(Screen):
    CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-panel {
        width: 60;
        height: auto;
        border: solid #9A968B;
        padding: 1 2;
        background: #1e1e1e;
        color: #c9c7c0;
    }
    .help-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #help-hint {
        color: #9A968B;
        margin-top: 1;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Back"),
    ]

    _CMDS = [
        ("/stop",     "Stop all sessions (bot stays running)"),
        ("/start",    "Resume sessions after /stop"),
        ("/exit",     "Fully exit the bot"),
        ("/settings", "Open settings panel"),
        ("/save-log", "Save a plain text copy of the log"),
        ("/help",     "Show this screen"),
        ("Esc",       "Return to main view"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-panel"):
            yield Static("Help", classes="help-title")
            for cmd, desc in self._CMDS:
                row = Text()
                row.append(f"{cmd:<12}", style="#adcc00")
                row.append(desc, style="#9A968B")
                yield Static(row)
            yield Static("Esc: Close", id="help-hint")


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class BurnBotApp(App):

    CSS = """
    Screen {
        background: #1a1a1a;
        layers: base overlay;
        color: #c9c7c0;
    }

    #header-bar {
        height: 2;
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
        padding: 0 1;
    }
    Input:focus {
        border: none;
    }
    #cmd-ghost {
        width: 1fr;
        color: #4a4a45;
        background: #1a1a1a;
        content-align: left middle;
        padding: 0;
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
            yield DataTable(id="settings-table", show_header=False, cursor_type="row")
            yield Static("Enter: Toggle   Esc: Back", id="settings-hint")
        yield DataTable(id="accounts", show_cursor=False)
        with Horizontal(id="input-row"):
            yield Static(">", id="input-prompt")
            with Horizontal(id="cmd-inner"):
                yield Input(placeholder="enter a command", id="cmd-input")
                yield Static("", id="cmd-ghost")
            yield Static("", id="input-hints")

    def on_mount(self) -> None:
        accounts = self.query_one("#accounts", DataTable)
        accounts.add_column("Account",        key="account")
        accounts.add_column("Status",         key="status")
        accounts.add_column("Sessions Today", key="sessions_today")
        accounts.add_column("Next Run",       key="next_run")
        accounts.add_column("Last Action",    key="last_action")

        settings = self.query_one("#settings-table", DataTable)
        settings.add_columns("Setting", "Value")

        self._refresh_header()
        self.set_interval(1.0, self._refresh_header)
        self.query_one("#cmd-input", Input).focus()
        status_store.flush_log_buffer(self)
        threading.Thread(target=self._bot_loop_fn, daemon=True).start()

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
        self.query_one("#log").display = False
        self.query_one("#settings-overlay").display = True
        self._refresh_settings_rows()
        self.query_one("#settings-table", DataTable).focus()

    def _close_settings(self) -> None:
        self.query_one("#settings-overlay").display = False
        self.query_one("#log").display = True
        self.query_one("#cmd-input", Input).focus()

    def _refresh_settings_rows(self) -> None:
        table = self.query_one("#settings-table", DataTable)
        saved_row = table.cursor_row
        table.clear()
        for label, key in status_store._SETTINGS:
            val = status_store.get_setting_value(key)
            val_text = Text("ON", style="#adcc00") if val else Text("OFF", style="#cf3b0a")
            table.add_row(label, val_text)
        if saved_row < len(status_store._SETTINGS):
            table.move_cursor(row=saved_row)

    @on(DataTable.RowSelected)
    def on_settings_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "settings-table":
            status_store.toggle_setting(event.cursor_row)
            self._refresh_settings_rows()

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
            table.update_cell(account_name, "last_action",    last_action,  update_width=False)
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
        typed = self.query_one("#cmd-input", Input).value
        if self._completions:
            current = self._completions[self._completion_idx]
            suffix  = current[len(typed):]
            count   = len(self._completions)
            label   = suffix if count == 1 else f"{suffix}  [{self._completion_idx + 1}/{count}]"
            ghost.update(label)
        else:
            ghost.update("")

    @on(Input.Changed, "#cmd-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        typed = event.value
        if typed and typed.startswith("/") and len(typed) > 1:
            self._completions = [c for c in self._COMMANDS if c.startswith(typed) and c != typed]
        else:
            self._completions = []
        self._completion_idx = 0
        self._update_ghost()

    def on_key(self, event) -> None:
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
        event.input.clear()
        if not cmd:
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
            self.push_screen(HelpScreen())
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
        if inp.value:
            inp.clear()
        elif self.query_one("#settings-overlay").display:
            self._close_settings()
        elif self.screen_stack and len(self.screen_stack) > 1:
            self.pop_screen()
