# burnBot_run_log.py
#
# Durable, cross-run diagnostics for the bot client:
#   - a rotating file sink mirroring everything the TUI shows, tagged with a
#     run id + session id so lines from one account/session can be grepped
#     out of a multi-account log
#   - failure-artifact capture (screenshot + page source + a diagnostic
#     summary) for post-mortem review
#   - a fire-and-forget uploader that posts a compact failure record to the
#     backend (POST /bot/activity-log, kind="failure") so it shows up
#     without shell access to the container
#
# Deliberately separate from burnBot_client_log.py, which must stay a pure
# zero-I/O string formatter — it is imported at module-load time by nearly
# every file, before config (and therefore /data) is known. Nothing in this
# module may raise into a caller; every public function is a safe no-op on
# failure, because diagnostics must never break a bot run.

import atexit
import json
import logging
import logging.handlers
import os
import queue
import threading
import time
import uuid
from datetime import datetime

from burnBot_config import CONFIG, resolve_path

try:
    from burnBot_version import BOT_VERSION
except Exception:
    BOT_VERSION = "?"


RUN_ID = f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"

_LOGGER_NAME = "slowburn"
_logger = logging.getLogger(_LOGGER_NAME)
_logger.propagate = False  # stdout/TUI already gets these lines via add_log()

_sink_lock = threading.Lock()
_sink_ready = False
_log_dir = None  # resolved once init_file_sink() succeeds

_context = threading.local()

_ARTIFACT_MAX_DIRS = 50
_ARTIFACT_MAX_BYTES = 200 * 1024 * 1024  # 200 MB

_LEVEL_KEYWORDS = (
    ("error", "ERROR"),
    ("fatal", "ERROR"),
    ("warning", "WARN"),
    ("debug", "DEBUG"),
)


# ---------------------------------------------------------------------------
# Session correlation
# ---------------------------------------------------------------------------

def set_session_context(account, session_id) -> None:
    """Tag every file-log line written by this thread with account/session,
    for the duration of one accountSession run. Call from the session thread
    only — the tag is thread-local."""
    _context.account = account
    _context.session_id = session_id


def clear_session_context() -> None:
    _context.account = None
    _context.session_id = None


def _current_session_tag() -> str:
    return getattr(_context, "session_id", None) or "-"


# ---------------------------------------------------------------------------
# File sink
# ---------------------------------------------------------------------------

def init_file_sink() -> None:
    """Set up the rotating file handler. Idempotent; safe to call more than
    once (e.g. on config reload). Must be called after load_config()."""
    global _sink_ready, _log_dir
    with _sink_lock:
        if _sink_ready:
            return
        try:
            log_dir = resolve_path(CONFIG.get("bot_settings", "log_dir", fallback="logs"))
            os.makedirs(log_dir, exist_ok=True)
            handler = logging.handlers.RotatingFileHandler(
                os.path.join(log_dir, "slowburnbot.log"),
                maxBytes=5_000_000,
                backupCount=5,
                encoding="utf-8",
                delay=True,
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            _logger.handlers = [handler]
            _logger.setLevel(logging.DEBUG)
            _log_dir = log_dir
            _sink_ready = True
        except Exception:
            pass  # diagnostics must never throw — the TUI still works without a file sink


def _guess_level(raw_line: str) -> str:
    low = raw_line.lower()
    for needle, level in _LEVEL_KEYWORDS:
        if needle in low:
            return level
    return "INFO"


def write_line(raw_line: str, level: str = None) -> None:
    """Append one line to the rotating file log. No-ops silently until
    init_file_sink() has run. Never raises."""
    if not _sink_ready:
        return
    try:
        lvl = level or _guess_level(raw_line)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        _logger.info(
            "%s %-5s run=%s ses=%s | %s",
            ts, lvl, RUN_ID, _current_session_tag(), raw_line,
        )
    except Exception:
        pass


def log_event(level: str, account, scope: str, message: str) -> str:
    """Build + return a client_log_line-shaped string and write it straight
    to the file sink at an explicit level (bypassing the TUI's own tap so
    callers that already print through add_log don't get double-written —
    use this only for lines that are file-only, e.g. suppressed non-debug
    detail). Most callers should keep printing via _print() as before; the
    add_log() tap handles the file write for those automatically."""
    from burnBot_client_log import client_log_line
    line = client_log_line(account, scope, message)
    write_line(line, level=level)
    return line


# ---------------------------------------------------------------------------
# Diagnostic capture (generalizes burnBot_login._capture_page_diag /
# _save_login_screenshot — see plan §0 "Reuse, don't rewrite")
# ---------------------------------------------------------------------------

def capture_page_diag(driver):
    """
    Capture page URL, visible button texts, role-button/link texts, iframe
    count, body text, and a page source snippet for element-not-found
    diagnostics. Returns (log_str, print_str) — log_str is compact (URL +
    element counts); print_str also includes body/source.

    Relocated verbatim from burnBot_login._capture_page_diag.
    """
    try:
        from burnBot_imports import By

        page_url = driver.current_url
        buttons = driver.find_elements(By.TAG_NAME, "button")
        btn_texts = [b.text.strip() for b in buttons if b.text.strip()]
        role_buttons = driver.find_elements(By.XPATH, "//*[@role='button']")
        role_btn_texts = [b.text.strip() for b in role_buttons if b.text.strip()][:8]
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        iframe_count = len(iframes)
        body_text = driver.execute_script(
            "return (document.body && document.body.innerText) "
            "? document.body.innerText.slice(0, 1500) : '(no body)'"
        ).replace("\n", " ")
        src_snippet = (driver.page_source or "")[:2000].replace("\n", " ")
        log_str = (
            f"url={page_url} | buttons={btn_texts} | role_buttons={role_btn_texts}"
            f" | iframes={iframe_count}"
        )
        print_str = f"[login-diag] {log_str} | body={body_text} | src={src_snippet}"
        return log_str, print_str
    except Exception:
        return "", ""


def _artifact_dir_for(account, stage_slug) -> str:
    safe_acct = (account or "unknown").replace("/", "_").replace(os.sep, "_")
    safe_stage = "".join(c if (c.isalnum() or c in "-_") else "-" for c in (stage_slug or "stage"))
    day = datetime.now().strftime("%Y%m%d")
    hms = datetime.now().strftime("%H%M%S")
    return os.path.join(_log_dir, "artifacts", day, safe_acct, f"{hms}_{safe_stage}")


def capture_failure_artifact(driver, account, stage, note="", account_id=None) -> str:
    """
    Save a screenshot, truncated page source, and a diagnostic text summary
    under <log_dir>/artifacts/<date>/<account>/<time>_<stage>/. Generalizes
    burnBot_login._save_login_screenshot. Returns the artifact directory
    path (relative to log_dir) on success, "" on any failure. Never raises —
    diagnostics must never break a run.
    """
    if not _sink_ready or driver is None:
        return ""
    try:
        art_dir = _artifact_dir_for(account, stage)
        os.makedirs(art_dir, exist_ok=True)

        try:
            driver.save_screenshot(os.path.join(art_dir, "page.png"))
        except Exception:
            pass

        try:
            src = (driver.page_source or "")[:512_000]
            with open(os.path.join(art_dir, "page.html"), "w", encoding="utf-8") as fh:
                fh.write(src)
        except Exception:
            pass

        try:
            log_str, print_str = capture_page_diag(driver)
            current_url = ""
            try:
                current_url = driver.current_url or ""
            except Exception:
                pass
            diag_lines = [
                f"run={RUN_ID}",
                f"ses={_current_session_tag()}",
                f"ver={BOT_VERSION}",
                f"stage={stage}",
                f"note={note}",
                f"url={current_url}",
                print_str or log_str,
            ]
            with open(os.path.join(art_dir, "diag.txt"), "w", encoding="utf-8") as fh:
                fh.write("\n".join(diag_lines))
        except Exception:
            pass

        rel_dir = os.path.relpath(art_dir, _log_dir)
        try:
            _prune_artifacts()
        except Exception:
            pass
        return rel_dir
    except Exception:
        return ""


def _prune_artifacts() -> None:
    """Delete oldest artifact leaf dirs until under the dir-count and
    byte-size caps. Best-effort; never raises."""
    root = os.path.join(_log_dir, "artifacts")
    if not os.path.isdir(root):
        return

    leaf_dirs = []
    for day_entry in os.scandir(root):
        if not day_entry.is_dir():
            continue
        for acct_entry in os.scandir(day_entry.path):
            if not acct_entry.is_dir():
                continue
            for stage_entry in os.scandir(acct_entry.path):
                if stage_entry.is_dir():
                    leaf_dirs.append(stage_entry.path)

    def _dir_size(path):
        total = 0
        for dirpath, _dirnames, filenames in os.walk(path):
            for fn in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, fn))
                except OSError:
                    pass
        return total

    entries = sorted(
        ((p, os.path.getmtime(p), _dir_size(p)) for p in leaf_dirs),
        key=lambda e: e[1],
    )
    total_bytes = sum(e[2] for e in entries)

    import shutil
    while entries and (len(entries) > _ARTIFACT_MAX_DIRS or total_bytes > _ARTIFACT_MAX_BYTES):
        path, _mtime, size = entries.pop(0)
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass
        total_bytes -= size


# ---------------------------------------------------------------------------
# Backend failure upload — fire-and-forget, never blocks the automation loop
# ---------------------------------------------------------------------------

_failure_queue: "queue.Queue" = queue.Queue(maxsize=200)
_uploader_started = False
_uploader_lock = threading.Lock()


def _ensure_uploader_started() -> None:
    global _uploader_started
    with _uploader_lock:
        if _uploader_started:
            return
        t = threading.Thread(target=_uploader_loop, daemon=True, name="failure-uploader")
        t.start()
        atexit.register(_drain_on_exit)
        _uploader_started = True


def _uploader_loop() -> None:
    while True:
        item = _failure_queue.get()
        if item is None:
            return
        account_id, stage, status, payload = item
        try:
            from burnBot_apiClient import get_shared_client
            client = get_shared_client()
            if client is not None and account_id:
                details = json.dumps(payload, default=str)[:8000]
                client.log_activity(account_id, stage, status, details, kind="failure")
        except Exception:
            pass  # diagnostics must never throw


def _drain_on_exit() -> None:
    try:
        _failure_queue.put_nowait(None)
    except Exception:
        pass


def report_failure(account_id, stage, status, payload: dict) -> None:
    """
    Enqueue a structured failure record for background upload to the
    backend. Never blocks — a full queue drops the record silently rather
    than stalling the automation thread on a slow/offline API call.
    """
    try:
        _ensure_uploader_started()
        record = dict(payload or {})
        record.setdefault("run", RUN_ID)
        record.setdefault("ses", _current_session_tag())
        record.setdefault("ver", BOT_VERSION)
        record.setdefault("stage", stage)
        record.setdefault("elapsed_ms", None)
        _failure_queue.put_nowait((account_id, stage, status, record))
    except queue.Full:
        pass
    except Exception:
        pass
