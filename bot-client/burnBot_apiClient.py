# burnBot_apiClient.py
# Replaces burnBot_driveManager.py — all data access goes through the FastAPI backend

import threading
import time
from datetime import datetime, date

import httpx


def _as_local_aware(dt):
    """Local wall time as timezone-aware so ISO strings include offset (avoids server treating naive as UTC)."""
    if not isinstance(dt, datetime):
        return dt
    if dt.tzinfo is None:
        return dt.astimezone()
    return dt
import keyring

KEYRING_SERVICE = "SlowBurnBot"
KEYRING_TOKEN_KEY = "access_token"


class ApiClient:
    """
    Thread-safe HTTP client that replaces DriveManager.
    All Google Sheets operations are now API calls to the FastAPI backend.
    """

    def __init__(self, api_url):
        self.api_url = api_url.rstrip("/")
        self.client = httpx.Client(base_url=self.api_url, timeout=30)
        self._token_lock = threading.Lock()
        self._access_token = None

        # Caches
        self._settings_cache = {}       # {account_id: (data, timestamp)}
        self._settings_cache_ttl = 300  # 5 minutes
        self._ignore_cache = None
        self._ignore_cache_ts = 0.0
        self._ignore_cache_ttl = 300

        # Load token from keyring on startup
        self._load_token()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _load_token(self):
        """Load access token from Windows keyring."""
        token = keyring.get_password(KEYRING_SERVICE, KEYRING_TOKEN_KEY)
        if token:
            self._access_token = token

    def _save_token(self):
        """Save access token to Windows keyring."""
        if self._access_token:
            keyring.set_password(KEYRING_SERVICE, KEYRING_TOKEN_KEY, self._access_token)

    def _clear_token(self):
        """Remove stored token."""
        self._access_token = None
        try:
            keyring.delete_password(KEYRING_SERVICE, KEYRING_TOKEN_KEY)
        except keyring.errors.PasswordDeleteError:
            pass

    def _auth_headers(self):
        """Return Authorization header dict."""
        if not self._access_token:
            return {}
        return {"Authorization": f"Bearer {self._access_token}"}

    def has_token(self):
        """Check if we have an access token (may or may not be valid)."""
        return self._access_token is not None

    def login(self, email, password):
        """
        Authenticate with the API and store the JWT token.
        Returns True on success, False on failure.
        """
        try:
            resp = self.client.post(
                "/auth/jwt/login",
                data={"username": email, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code == 200:
                data = resp.json()
                self._access_token = data["access_token"]
                self._save_token()
                return True
            else:
                print(f"[api]: Login failed (HTTP {resp.status_code})")
                return False
        except Exception as e:
            print(f"[api]: Login error: {e}")
            return False

    def refresh_token(self):
        """
        Refresh the access token using the current (still-valid) token.
        Returns True on success, False on failure.
        """
        with self._token_lock:
            try:
                resp = self.client.post(
                    "/auth/jwt/refresh",
                    headers=self._auth_headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    self._access_token = data["access_token"]
                    self._save_token()
                    return True
                else:
                    return False
            except Exception:
                return False

    def _request(self, method, path, **kwargs):
        """
        Make an authenticated request with auto-retry on 401.
        Raises an exception on persistent auth failure.
        """
        headers = kwargs.pop("headers", {})
        headers.update(self._auth_headers())

        resp = self.client.request(method, path, headers=headers, **kwargs)

        if resp.status_code == 401:
            # Try refreshing the token once
            if self.refresh_token():
                headers.update(self._auth_headers())
                resp = self.client.request(method, path, headers=headers, **kwargs)
            if resp.status_code == 401:
                self._clear_token()
                raise AuthenticationError("Session expired. Please log in again.")

        if resp.status_code == 402:
            raise SubscriptionRequiredError("Active subscription required.")

        resp.raise_for_status()
        return resp

    # ------------------------------------------------------------------
    # Entitlement
    # ------------------------------------------------------------------

    def check_entitlement(self):
        """
        Check subscription status. Returns dict with:
            active (bool), plan_tier (str), current_period_end (str|None)
        """
        resp = self._request("GET", "/bot/entitlement")
        return resp.json()

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    def get_accounts(self, group_number=None):
        """
        Fetch all accounts for the user, optionally filtered by group.
        Returns list of account dicts.
        """
        params = {}
        if group_number is not None:
            params["group_number"] = group_number
        resp = self._request("GET", "/accounts", params=params)
        return resp.json()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def get_account_settings(self, account_id):
        """
        Fetch account settings. Cached for _settings_cache_ttl seconds.
        Returns dict or None.
        """
        now = time.time()
        cached = self._settings_cache.get(account_id)
        if cached and (now - cached[1]) < self._settings_cache_ttl:
            return cached[0]

        try:
            resp = self._request("GET", f"/bot/settings/{account_id}")
            data = resp.json()
            self._settings_cache[account_id] = (data, now)
            return data
        except Exception as e:
            # Return cached data if available, even if stale
            if cached:
                return cached[0]
            print(f"[api]: Failed to fetch settings for {account_id}: {e}")
            return None

    def invalidate_settings_cache(self, account_id=None):
        """Force refresh on next settings fetch."""
        if account_id:
            self._settings_cache.pop(account_id, None)
        else:
            self._settings_cache.clear()

    # ------------------------------------------------------------------
    # Credentials
    # ------------------------------------------------------------------

    def get_ig_password(self, account_id):
        """Fetch decrypted IG password for an account."""
        try:
            resp = self._request("GET", f"/bot/credentials/{account_id}")
            return resp.json().get("ig_password")
        except Exception as e:
            print(f"[api]: Failed to fetch credentials for {account_id}: {e}")
            return None

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log_session_run(self, account_id, start_time, end_time,
                        action1_type="", action1_count=0,
                        action2_type="", action2_count=0,
                        action3_type="", action3_count=0,
                        action4_type="", action4_count=0,
                        error_message="", run_sequence=1):
        """
        Post a session log to the API.
        Returns dict with 'id' on success, None on failure.
        """
        if isinstance(start_time, datetime):
            start_time = _as_local_aware(start_time)
        if isinstance(end_time, datetime):
            end_time = _as_local_aware(end_time)
        payload = {
            "account_id": str(account_id),
            "run_date": start_time.strftime("%Y-%m-%d") if isinstance(start_time, datetime) else str(start_time),
            "run_sequence": run_sequence,
            "start_time": start_time.isoformat(timespec="seconds") if isinstance(start_time, datetime) else None,
            "end_time": end_time.isoformat(timespec="seconds") if isinstance(end_time, datetime) else None,
            "action_1_type": action1_type or None,
            "action_1_count": action1_count,
            "action_2_type": action2_type or None,
            "action_2_count": action2_count,
            "action_3_type": action3_type or None,
            "action_3_count": action3_count,
            "action_4_type": action4_type or None,
            "action_4_count": action4_count,
            "error_message": error_message or None,
        }
        try:
            resp = self._request("POST", "/bot/session-log", json=payload)
            return resp.json()
        except Exception as e:
            print(f"[api]: Failed to log session: {e}")
            return None

    def log_activity(self, account_id, action, status, details=""):
        """Post a fine-grained activity log."""
        payload = {
            "account_id": str(account_id),
            "kind": "activity",
            "action": action,
            "status": status,
            "details": details or None,
        }
        try:
            self._request("POST", "/bot/activity-log", json=payload)
        except Exception as e:
            print(f"[api]: Failed to log activity: {e}")

    def log_error(self, account_id, error_message):
        """Post an error log entry."""
        payload = {
            "account_id": str(account_id),
            "kind": "error",
            "action": "error",
            "status": "failed",
            "details": error_message,
        }
        try:
            self._request("POST", "/bot/activity-log", json=payload)
        except Exception as e:
            print(f"[api]: Failed to log error: {e}")

    # ------------------------------------------------------------------
    # Follow targets
    # ------------------------------------------------------------------

    def get_follow_targets(self, account_id, status=None, older_than_days=None, page=1, page_size=500):
        """
        Fetch follow targets for an account with optional filtering.
        Returns list of target dicts.
        """
        params = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status
        if older_than_days is not None:
            params["older_than_days"] = older_than_days
        try:
            resp = self._request("GET", f"/bot/follow-targets/{account_id}", params=params)
            return resp.json()
        except Exception as e:
            print(f"[api]: Failed to fetch follow targets: {e}")
            return []

    def get_all_follow_target_handles(self, account_id):
        """
        Fetch ALL follow target handles for duplicate checking.
        Pages through results automatically. Returns set of lowercase handles.
        """
        handles = set()
        page = 1
        while True:
            targets = self.get_follow_targets(account_id, page=page, page_size=5000)
            if not targets:
                break
            for t in targets:
                handles.add(t["target_handle"].lower())
            if len(targets) < 5000:
                break
            page += 1
        return handles

    def create_follow_target(self, account_id, target_handle, source=None, status="following", follow_date=None):
        """Create a new follow target record."""
        payload = {
            "account_id": str(account_id),
            "target_handle": target_handle,
            "source": source,
            "status": status,
            "follow_date": follow_date.isoformat() if isinstance(follow_date, date) else follow_date,
        }
        try:
            resp = self._request("POST", "/bot/follow-targets", json=payload)
            return resp.json()
        except Exception as e:
            print(f"[api]: Failed to create follow target: {e}")
            return None

    def update_follow_target(self, target_id, status=None, unfollow_date=None, follow_back=None):
        """Update a follow target (status, unfollow_date, follow_back)."""
        payload = {}
        if status is not None:
            payload["status"] = status
        if unfollow_date is not None:
            payload["unfollow_date"] = unfollow_date.isoformat() if isinstance(unfollow_date, date) else unfollow_date
        if follow_back is not None:
            payload["follow_back"] = follow_back
        try:
            resp = self._request("PATCH", f"/bot/follow-targets/{target_id}", json=payload)
            return resp.json()
        except Exception as e:
            print(f"[api]: Failed to update follow target: {e}")
            return None

    # ------------------------------------------------------------------
    # Ignore list
    # ------------------------------------------------------------------

    def get_ignore_handles(self):
        """
        Fetch the user's ignore list. Cached for _ignore_cache_ttl seconds.
        Returns list of handle strings.
        """
        now = time.time()
        if self._ignore_cache is not None and (now - self._ignore_cache_ts) < self._ignore_cache_ttl:
            return self._ignore_cache

        try:
            resp = self._request("GET", "/bot/ignore-handles")
            handles = resp.json().get("handles", [])
            self._ignore_cache = handles
            self._ignore_cache_ts = now
            return handles
        except Exception as e:
            if self._ignore_cache is not None:
                return self._ignore_cache
            print(f"[api]: Failed to fetch ignore handles: {e}")
            return []

    # ------------------------------------------------------------------
    # Notification credentials (system-wide SMTP/TextBelt)
    # ------------------------------------------------------------------

    _notif_creds_cache = None
    _notif_creds_cache_ts = 0.0
    _notif_creds_cache_ttl = 300  # 5 minutes

    def get_notification_credentials(self):
        """
        Fetch system-wide SMTP/TextBelt credentials from the API.
        Cached for _notif_creds_cache_ttl seconds.
        Returns dict with smtp_server, smtp_port, smtp_user, smtp_password, textbelt_key.
        """
        now = time.time()
        if self._notif_creds_cache is not None and (now - self._notif_creds_cache_ts) < self._notif_creds_cache_ttl:
            return self._notif_creds_cache

        try:
            resp = self._request("GET", "/bot/notification-credentials")
            data = resp.json()
            self._notif_creds_cache = data
            self._notif_creds_cache_ts = now
            return data
        except Exception as e:
            if self._notif_creds_cache is not None:
                return self._notif_creds_cache
            print(f"[api]: Failed to fetch notification credentials: {e}")
            return None

    # ------------------------------------------------------------------
    # User config (notification prefs)
    # ------------------------------------------------------------------

    _config_cache = None
    _config_cache_ts = 0.0
    _config_cache_ttl = 300  # 5 minutes

    def get_user_config(self):
        """
        Fetch user-wide config (notification prefs) from the API.
        Cached for _config_cache_ttl seconds.
        Returns dict with notices_type, notices_session, notify_email, notify_phone.
        """
        now = time.time()
        if self._config_cache is not None and (now - self._config_cache_ts) < self._config_cache_ttl:
            return self._config_cache

        try:
            resp = self._request("GET", "/bot/config")
            data = resp.json()
            self._config_cache = data
            self._config_cache_ts = now
            return data
        except Exception as e:
            if self._config_cache is not None:
                return self._config_cache
            print(f"[api]: Failed to fetch user config: {e}")
            return None

    # ------------------------------------------------------------------
    # Run count
    # ------------------------------------------------------------------

    def get_run_count(self, account_id, run_date=None):
        """
        Get session log count for an account on a given date (defaults to today).
        Returns int.
        """
        params = {}
        if run_date:
            params["run_date"] = run_date.isoformat() if isinstance(run_date, date) else run_date
        try:
            resp = self._request("GET", f"/bot/run-count/{account_id}", params=params)
            return resp.json().get("count", 0)
        except Exception as e:
            print(f"[api]: Failed to fetch run count: {e}")
            return 0


# ------------------------------------------------------------------
# Custom exceptions
# ------------------------------------------------------------------

class AuthenticationError(Exception):
    """Raised when the user needs to re-authenticate."""
    pass


class SubscriptionRequiredError(Exception):
    """Raised when an active subscription is required (HTTP 402)."""
    pass
