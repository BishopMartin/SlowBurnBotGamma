# burnBot_client_log.py — unified TUI / client log line shape
from __future__ import annotations

from datetime import datetime
from typing import Optional

ACCOUNT_COL = 18
SCOPE_COL = 16


def log_sanitize(text: str) -> str:
    if not text:
        return ""
    return text.replace("\x00", "")


def mask_email(email: str) -> str:
    s = (email or "").strip()
    if not s or "@" not in s:
        return s or "—"
    local, _, domain = s.partition("@")
    if len(local) <= 2:
        return f"{local[0]}***@{domain}" if local else f"***@{domain}"
    return f"{local[:2]}***@{domain}"


def mask_phone(phone: str) -> str:
    s = "".join(c for c in (phone or "") if c.isdigit())
    if len(s) < 4:
        return "***" if phone and phone.strip() else "—"
    return f"***{s[-4:]}"


def _truncate_account(name: str, width: int) -> str:
    n = log_sanitize(name)
    if len(n) <= width:
        return n
    if width <= 1:
        return "…"
    return n[: width - 1] + "…"


def client_log_line(account: Optional[str], scope: str, message: str = "") -> str:
    """One log line: HH:MM:SS  account  scope  message (account column omitted when empty)."""
    ts = datetime.now().strftime("%H:%M:%S")
    sc = log_sanitize((scope or "").strip())[:32]
    msg = log_sanitize(str(message))
    acct_raw = (account or "").strip()
    if acct_raw:
        acct = _truncate_account(acct_raw, ACCOUNT_COL)
        return f"{ts}  {acct:<{ACCOUNT_COL}}  {sc:<{SCOPE_COL}}  {msg}".rstrip()
    return f"{ts}  {sc:<{SCOPE_COL}}  {msg}".rstrip()


def action_combo_slug(act_type: str, act_target: str) -> Optional[str]:
    """Hyphenated action-target for dashboard/API type+target pairs (single source of truth)."""
    t = (act_type or "").strip().lower()
    g = (act_target or "").strip().lower()
    if t == "like":
        if g in ("home", "homepage posts", "post[homepage]", "posts [homepage]"):
            return "like-home"
        if g in ("post[topics]", "posts [topics]"):
            return "like-topics"
    if t == "follow":
        if g in ("suggested", "home", "homepage", "suggested users"):
            return "follow-suggested"
        if g in (
            "followers[group]",
            "following[group]",
            "account list [followers]",
            "account list [following]",
        ):
            return "follow-group"
    if t == "unfollow":
        if g == "database":
            return "unfollow-database"
        if g == "previous follows":
            return "unfollow-previous"
    return None


def follow_group_variant_label(group_type: str) -> str:
    """Short suffix for follow-group logs (followers vs following list)."""
    g = (group_type or "").strip().lower()
    if "follower" in g:
        return "followers"
    if "following" in g:
        return "following"
    return g or "group"
