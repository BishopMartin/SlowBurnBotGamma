# burnBot_app.py — Textual TUI for SlowBurnBot client

import threading
from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Input, RichLog, Rule, Static
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual import on
from rich.text import Text

import burnBot_status as status_store


# ---------------------------------------------------------------------------
# Settings overlay screen
# ---------------------------------------------------------------------------

class SettingsScreen(Screen):
    CSS = """
    SettingsScreen {
        align: center middle;
    }
    #settings-panel {
        width: 50;
        height: auto;
        border: solid #9A968B;
        padding: 1 2;
        background: #1e1e1e;
    }
    .settings-title {
        text-align: center;
        color: #f4f3ee;
        text-style: bold;
        margin-bottom: 1;
    }
    .settings-row {
        height: 1;
    }
    #settings-hint {
        color: #9A968B;
        margin-top: 1;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Back"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-panel"):
            yield Static("Settings", classes="settings-title")
            yield DataTable(id="settings-table", show_header=False, cursor_type="row")
            yield Static("Enter: Toggle   Esc: Back", id="settings-hint")

    def on_mount(self) -> None:
        table = self.query_one("#settings-table", DataTable)
        table.add_columns("Setting", "Value")
        self._refresh_rows()
        table.focus()

    def _refresh_rows(self) -> None:
        table = self.query_one("#settings-table", DataTable)
        table.clear()
        for label, key in status_store._SETTINGS:
            val = status_store.get_setting_value(key)
            val_text = Text("ON", style="#adcc00") if val else Text("OFF", style="#cf3b0a")
            table.add_row(label, val_text)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        status_store.toggle_setting(event.cursor_row)
        self._refresh_rows()


# ---------------------------------------------------------------------------
# Help overlay screen
# ---------------------------------------------------------------------------

class HelpScreen(Screen):
    CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-panel {
        width: 54;
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
        height: 1;
        background: #1a1a1a;
        color: #f4f3ee;
        padding: 0 1;
    }

    Rule {
        color: #3a3a3a;
        margin: 0;
    }

    RichLog {
        border: none;
        background: #1a1a1a;
        color: #c9c7c0;
        padding: 0 0 0 1;
        scrollbar-color: #9A968B;
        scrollbar-background: #1a1a1a;
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
    Input {
        background: #1a1a1a;
        color: #f4f3ee;
        border: none;
    }
    Input:focus {
        border: none;
    }
    """

    BINDINGS = [
        Binding("escape", "clear_input", "Clear", show=False),
    ]

    def __init__(self, version: str, client_id: str, client_name: str,
                 bot_loop_fn, stop_flag):
        super().__init__()
        self._version     = version
        self._client_id   = client_id
        self._client_name = client_name
        self._bot_loop_fn = bot_loop_fn
        self._stop_flag   = stop_flag

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Static("", id="header-bar")
        yield Rule()
        yield RichLog(highlight=False, markup=True, wrap=False, id="log")
        yield DataTable(id="accounts", show_cursor=False)
        with Horizontal(id="input-row"):
            yield Static(">", id="input-prompt")
            yield Input(placeholder="type a command  ·  /stop   /exit   /settings   /help", id="cmd-input")

    def on_mount(self) -> None:
        table = self.query_one("#accounts", DataTable)
        table.add_columns("Account", "Status", "Sessions Today", "Next Run", "Last Action")
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
            header.append("[STOPPED]", style="bold #E5C07B")
        else:
            header.append("[RUNNING]", style="bold #adcc00")

        self.query_one("#header-bar", Static).update(header)

        try:
            inp = self.query_one("#cmd-input", Input)
            hint_cmd = "/start" if paused else "/stop"
            inp.placeholder = f"type a command  ·  {hint_cmd}   /exit   /settings   /help"
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Log + accounts table (called from bot threads via call_from_thread)
    # ------------------------------------------------------------------

    def _write_log(self, line: str) -> None:
        self.query_one("#log", RichLog).write(line)

    def _update_account_row(self, account_name: str, kwargs: dict) -> None:
        table  = self.query_one("#accounts", DataTable)
        status = kwargs.get("status", "—")
        color  = status_store.COLOR.get(status, status_store.DIM)

        status_cell  = Text(status, style=color)
        run_info     = kwargs.get("run_info",    "—")
        next_run     = kwargs.get("next_run",    "—")
        last_action  = kwargs.get("last_action", "—")

        try:
            table.update_cell(account_name, "Status",         status_cell,  update_width=False)
            table.update_cell(account_name, "Sessions Today", run_info,     update_width=False)
            table.update_cell(account_name, "Next Run",       next_run,     update_width=False)
            table.update_cell(account_name, "Last Action",    last_action,  update_width=False)
        except Exception:
            table.add_row(
                account_name, status_cell, run_info, next_run, last_action,
                key=account_name,
            )

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
            self.push_screen(SettingsScreen())
        elif cmd == "/help":
            self.push_screen(HelpScreen())
        else:
            self._write_log(f"[{status_store.DIM}][[bot]][[user command]][/] - Unknown command '{cmd}' — type /help for list")

    def action_clear_input(self) -> None:
        inp = self.query_one("#cmd-input", Input)
        if inp.value:
            inp.clear()
        elif self.screen_stack and len(self.screen_stack) > 1:
            self.pop_screen()
