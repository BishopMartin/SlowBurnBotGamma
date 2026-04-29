# burnBot.py

from burnBot_imports import *
from burnBot_config import load_config, CONFIG, resolve_path, clear_api_credentials_in_ini, is_frozen
from burnBot_utils import close_windows, has_internet_connection, process_exception, delay, check_schedule, consume_connectivity_recovery_notice
from burnBot_accountSession import accountSession
from burnBot_accountSession_setup import is_bot_debug_enabled
from burnBot_apiClient import (
    ApiClient,
    AuthenticationError,
    SubscriptionRequiredError,
    get_stored_api_credentials,
    store_api_credentials,
)
from burnBot_runCounter import RunCounter
from burnBot_version import BOT_VERSION
import burnBot_status as status_store
from burnBot_app import BurnBotApp
from datetime import datetime, timedelta
import math
import socket

def _beep(kind):
    try:
        import winsound
        if kind == 'startup':
            winsound.Beep(523, 200)   # C5
            winsound.Beep(659, 200)   # E5
            winsound.Beep(784, 350)   # G5
        elif kind == 'shutdown':
            winsound.Beep(784, 200)   # G5
            winsound.Beep(659, 200)   # E5
            winsound.Beep(523, 400)   # C5
        elif kind == 'keypress':
            winsound.Beep(880, 150)
            winsound.Beep(660, 300)
    except Exception:
        pass

# Load config
config_file = load_config("burnBot_config.ini")

# Load API connection
api_url = CONFIG.get('api', 'api_url', fallback='')
if not api_url:
    print("ERROR: 'api_url' not set in [api] section of config file")
    sys.exit(1)

apiClient = ApiClient(api_url)

# Frozen EXE: perform one-time activation handshake before normal login
if is_frozen():
    try:
        import _desktop_build_config as _baked  # noqa: PLC0415
        status_store.add_log("[activation]: Activating desktop build...")
        apiClient.activate_desktop_build(
            user_id=_baked.USER_ID,
            client_id=_baked.CLIENT_ID,
            activation_token=_baked.ACTIVATION_TOKEN,
            bot_version=BOT_VERSION,
        )
        status_store.add_log("[activation]: Build activated.")
    except Exception as _act_err:
        print(f"[ERROR] Desktop activation failed: {_act_err}")
        sys.exit(1)


def _api_credentials_from_ini():
    email = CONFIG.get("api_credentials", "email", fallback="").strip()
    password = CONFIG.get("api_credentials", "password", fallback="").strip()
    return email, password


def _resolve_api_credentials():
    """Return (email, password, source).

    Prefers the OS keyring; falls back to the [api_credentials] section of
    the INI for one-time migration.  source is 'keyring', 'ini', or None.
    """
    email, password = get_stored_api_credentials()
    if email and password:
        return email, password, "keyring"
    email, password = _api_credentials_from_ini()
    if email and password:
        return email, password, "ini"
    return None, None, None


def _migrate_ini_credentials_to_keyring(email, password):
    """After first successful login from INI fallback, store in keyring and
    wipe the plaintext entries from the on-disk config."""
    try:
        store_api_credentials(email, password)
    except Exception as e:
        status_store.add_log(f"[api]: Could not store credentials in keyring: {e}")
        return
    if clear_api_credentials_in_ini():
        status_store.add_log("[api]: Plaintext credentials migrated from config to OS keyring.")


def _try_api_relogin_from_config(client):
    """Re-authenticate when the keyring JWT is stale.  Pulls creds from the
    keyring first, falls back to the INI for legacy installs."""
    email, password, source = _resolve_api_credentials()
    if not email or not password:
        return False
    status_store.add_log("[api]: Session expired — re-authenticating...")
    ok = client.login(email, password)
    if ok:
        status_store.add_log("[api]: Re-login OK.")
        if source == "ini":
            _migrate_ini_credentials_to_keyring(email, password)
    return bool(ok)


# Load bot_idle_delay for main loop check interval (in minutes, convert to seconds)
bot_idle_delay_minutes = CONFIG.getint('bot_settings', 'bot_idle_delay', fallback=1)
bot_idle_delay = bot_idle_delay_minutes * 60  # Convert to seconds

# Helper function for interruptible sleep
def sleep_with_interrupt_check(seconds, stop_flag, label=None, console=None):
    """Sleep for `seconds`, waking early if stop_flag is set. Returns True if interrupted."""
    intervals = int(seconds / 0.5)
    for _ in range(intervals):
        if stop_flag.is_set() or status_store.is_stop_requested():
            return True
        time.sleep(0.5)
    return False


# ------------------------------------------------------------------
# Authentication — prompt for login if no stored token
# ------------------------------------------------------------------
if not apiClient.has_token():
    stored_email, stored_password, source = _resolve_api_credentials()

    if stored_email and stored_password:
        status_store.add_log(f"[api]: Using stored credentials ({source})...")
        if apiClient.login(stored_email, stored_password):
            if source == "ini":
                _migrate_ini_credentials_to_keyring(stored_email, stored_password)
        else:
            status_store.add_log("[api]: Stored credentials failed. Falling back to manual entry.")

    if not apiClient.has_token():
        print("Login required.")
        print("=" * 60)
        email = input("Email: ").strip()
        password = input("Password: ").strip()
        if not apiClient.login(email, password):
            print("Login failed. Exiting.")
            sys.exit(1)
        # Persist to keyring so the next run can authenticate non-interactively.
        try:
            store_api_credentials(email, password)
        except Exception as e:
            print(f"[api]: Could not store credentials in keyring: {e}")

    status_store.add_log("[api]: Login successful.")

# ------------------------------------------------------------------
# Entitlement check
# ------------------------------------------------------------------
try:
    try:
        entitlement = apiClient.check_entitlement()
    except AuthenticationError:
        if _try_api_relogin_from_config(apiClient):
            entitlement = apiClient.check_entitlement()
        else:
            raise
    if not entitlement.get("active"):
        print("=" * 60)
        print("Subscription is not active.")
        print(f"Plan: {entitlement.get('plan_tier', 'free')}")
        print("Please activate your subscription at the dashboard.")
        print("=" * 60)
        sys.exit(1)
    status_store.add_log(f"[api]: Subscription active (plan: {entitlement.get('plan_tier')})")
except AuthenticationError:
    print("Session expired. Add email/password under [api_credentials] in burnBot_config.ini for auto re-login,")
    print("or run again and sign in when prompted.")
    sys.exit(1)
except Exception as e:
    print(f"Entitlement check failed: {e}")
    sys.exit(1)


# Account tracking data structures
all_accounts = []        # All account dicts from API
started_accounts = []    # Account names that have a running thread
enabled_accounts = {}    # {account_id: account_dict} for accounts to process
account_thread_index = {}  # Map account_name -> index in threads_active/threads lists

account_schedules = {}   # Store schedule data for each account (keyed by account name)
account_last_run = {}    # Track when each account last ran (datetime)
account_next_run = {}    # Track next scheduled run time (datetime) per account
threads = []
threads_active = []
stop_flag = threading.Event()  # Global stop flag for clean shutdown

# Initialize local run counter (persists across script restarts)
run_counter = RunCounter()

# Group filter
client_id = CONFIG.get('bot_settings', 'client_id', fallback='')

def normalize_group(value):
    s = str(value).strip() if value is not None else ""
    if not s:
        return ""
    try:
        return str(int(float(s)))
    except Exception:
        return s

client_id_norm = normalize_group(client_id)

try:
    # --- Startup display ---
    _w = 24  # label column width
    _sg = str(CONFIG.get('bot_settings', 'client_id', fallback='')).strip()
    try:
        _sg = f"{int(_sg):02d}"
    except Exception:
        pass
    _client_name = CONFIG.get('bot_settings', 'client_name', fallback='').strip()
    _ua  = CONFIG.get('bot_settings', 'system_user_agent', fallback='').strip()
    _cs  = CONFIG.get('bot_settings', 'close_browser_session', fallback='FALSE').strip().upper()
    _ce  = CONFIG.get('bot_settings', 'close_browser_exit',    fallback='FALSE').strip().upper()
    _dbg = CONFIG.get('bot_settings', 'bot_debug',             fallback='FALSE').strip().upper()
    _idl = str(bot_idle_delay_minutes).zfill(2)
    _st  = CONFIG.get('bot_settings', 'system_type',           fallback='').strip()
    _notif_cfg = apiClient.get_user_config() or {}
    _skl = str(_notif_cfg.get('skip_login_check', False)).upper()
    _lgt = str(_notif_cfg.get('login_tries', 3)).zfill(2)
    _lks = str(_notif_cfg.get('like_suggested', False)).upper()
    _lkp = str(_notif_cfg.get('like_sponsored', False)).upper()
    _ant = (_notif_cfg.get('notices_type') or 'none').strip()
    _ans = str(_notif_cfg.get('notices_session', False)).upper()
    _ane = (_notif_cfg.get('notify_email') or '').strip()
    _anp = (_notif_cfg.get('notify_phone') or '').strip()

    _p = 0.04  # seconds between each printed line

    # Pre-populate log buffer — visible in body panel from the first frame of Live
    _started_at = datetime.now().strftime("%I:%M %p")
    status_store.add_log(f"SlowBurnBot Client v{BOT_VERSION}  started {_started_at}")
    status_store.add_log("=" * 60)
    status_store.add_log("Bot Settings:")
    if not is_frozen():
        status_store.add_log(f"{'local config file:':<{_w}}[{config_file}]")
    status_store.add_log(f"{'api_url:':<{_w}}[{api_url}]")
    status_store.add_log(f"{'client_id:':<{_w}}[{_sg}]")
    status_store.add_log(f"{'system_type:':<{_w}}[{_st}]")
    status_store.add_log(f"{'debug:':<{_w}}[{_dbg}]")
    status_store.add_log(f"{'system_user_agent:':<{_w}}[{_ua}]")
    status_store.add_log(f"{'close_browser_session:':<{_w}}[{_cs}]")
    status_store.add_log(f"{'close_browser_exit:':<{_w}}[{_ce}]")
    status_store.add_log(f"{'bot_idle_delay:':<{_w}}[{_idl}]")
    status_store.add_log("Session Settings (from web app):")
    status_store.add_log(f"{'like_suggested:':<{_w}}[{_lks}]")
    status_store.add_log(f"{'like_sponsored:':<{_w}}[{_lkp}]")
    status_store.add_log(f"{'skip_login_check:':<{_w}}[{_skl}]")
    status_store.add_log(f"{'login_tries:':<{_w}}[{_lgt}]")
    status_store.add_log("Notification Settings (from web app):")
    status_store.add_log(f"{'notices_type:':<{_w}}[{_ant}]")
    status_store.add_log(f"{'notices_session:':<{_w}}[{_ans}]")
    status_store.add_log(f"{'notify_email:':<{_w}}[{_ane}]")
    status_store.add_log(f"{'notify_phone:':<{_w}}[{_anp}]")
    status_store.add_log("=" * 60)
    _beep('startup')

    # Resolve local IP for heartbeat reporting
    try:
        _local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        _local_ip = ""
    _heartbeat_system_type = _st

    # Background heartbeat: backend marks clients offline after 2 min, but the
    # main loop's bot_idle_delay can exceed that. Resend last known state every 60s.
    _hb_lock = threading.Lock()
    _hb_state = {"status": "idle", "account": None}

    def _send_hb(status, account):
        with _hb_lock:
            _hb_state["status"] = status
            _hb_state["account"] = account
        apiClient.send_heartbeat(client_id_norm, _heartbeat_system_type, _local_ip, status, account)

    def _heartbeat_loop():
        while not stop_flag.is_set():
            if stop_flag.wait(60):
                return
            with _hb_lock:
                status = _hb_state["status"]
                account = _hb_state["account"]
            apiClient.send_heartbeat(client_id_norm, _heartbeat_system_type, _local_ip, status, account)

    threading.Thread(target=_heartbeat_loop, daemon=True).start()

    class _BotConsole:
        @staticmethod
        def print(*args, **kwargs):
            status_store.add_log(" ".join(str(a) for a in args))

    console = _BotConsole()

    def _bot_loop():
        while True:
            current_time = datetime.now().astimezone()

            # Refresh account list from API each cycle
            try:
                group_param = int(client_id_norm) if client_id_norm else None
                refreshed_accounts = apiClient.get_accounts(group_number=group_param)
            except AuthenticationError:
                if _try_api_relogin_from_config(apiClient):
                    try:
                        refreshed_accounts = apiClient.get_accounts(group_number=group_param)
                    except AuthenticationError:
                        console.print("[system]: Session expired after re-login. Check [api_credentials] or dashboard.")
                        break
                else:
                    console.print("[system]: Session expired. Set [api_credentials] in burnBot_config.ini or restart and log in.")
                    break
            except Exception as e:
                if is_bot_debug_enabled():
                    console.print(f"[system]: Warning - account refresh failed, using cached values: {e}")
                refreshed_accounts = None

            if refreshed_accounts is not None:
                all_accounts = refreshed_accounts

            # Rebuild enabled accounts and update schedules
            enabled_accounts = {}
            for acct in all_accounts:
                account_name = acct.get("name", "")
                account_id = acct.get("id", "")
                is_enabled = acct.get("enabled", False)
                is_system_disabled = acct.get("system_disabled", False)

                if is_enabled and not is_system_disabled:
                    enabled_accounts[account_name] = acct

                # Fetch settings for schedule data (use cache)
                settings = apiClient.get_account_settings(account_id) if account_id else None

                if settings:
                    schedule_days = settings.get("schedule_days") or ""
                    schedule_start = settings.get("schedule_start") or ""
                    schedule_end = settings.get("schedule_end") or ""
                    delay_base = settings.get("delay_base_minutes", 60) or 60
                    delay_random = settings.get("delay_random_minutes", 0) or 0
                    schedule_max = settings.get("max_runs_per_day", 0) or 0

                    old_delay = account_schedules.get(account_name, {}).get('delay_sig')
                    new_delay_sig = (float(delay_base), float(delay_random))
                    if old_delay is not None and old_delay != new_delay_sig:
                        account_next_run[account_name] = None

                    account_schedules[account_name] = {
                        'days': schedule_days,
                        'start': schedule_start,
                        'end': schedule_end,
                        'delay': {'base': float(delay_base), 'random': float(delay_random)},
                        'delay_sig': new_delay_sig,
                        'max': int(schedule_max),
                        'start_random_offset': account_schedules.get(account_name, {}).get('start_random_offset'),
                        'last_offset_date': account_schedules.get(account_name, {}).get('last_offset_date'),
                    }

                # Ensure last run is loaded
                if account_name not in account_last_run:
                    account_last_run[account_name] = run_counter.get_last_run_time(account_name)

            # Show status for all accounts, trigger active ones if it's time to run
            _any_account_waiting = False  # Track if any account is in-schedule and waiting
            for acct in all_accounts:
                account_name = acct.get("name", "")
                account_id = acct.get("id", "")

                if account_name not in enabled_accounts:
                    skip_reasons = []
                    if acct.get("system_disabled"):
                        skip_reasons.append("system-disabled")
                    elif not acct.get("enabled"):
                        skip_reasons.append("disabled")
                    skip_msg = "/".join(skip_reasons) if skip_reasons else "disabled"
                    status_store.update(account_name, status=skip_msg, next_run="—", last_action="—", run_info="—")
                    continue

                # Pause check — user typed /pause at runtime
                if status_store.is_bot_paused():
                    run_count = run_counter.get_run_count(account_name)
                    schedule_max = account_schedules.get(account_name, {}).get('max', 0) or 0
                    run_info = f"[{run_count}/{int(schedule_max)}]" if schedule_max > 0 else f"[{run_count}]"
                    status_store.update(account_name, status="paused", next_run="—", run_info=run_info)
                    continue

                # Account is active - check schedule and timing
                if account_name not in account_schedules:
                    status_store.update(account_name, status="no schedule", next_run="—", run_info="—")
                    continue

                schedule = account_schedules[account_name]
                last_run = account_last_run.get(account_name)
                delay_config = schedule.get('delay', {'base': 60.0, 'random': 0.0})
                next_run_time = account_next_run.get(account_name)

                # Calculate daily random offset for start time
                today_date = current_time.date()
                if schedule.get('last_offset_date') != today_date:
                    random_start_offset = 0
                    if isinstance(delay_config, dict) and delay_config.get('random', 0) > 0:
                        random_start_offset = random.uniform(0, delay_config['random'])
                    schedule['start_random_offset'] = random_start_offset
                    schedule['last_offset_date'] = today_date

                # Apply random offset to start time
                adjusted_start = schedule['start']
                if schedule.get('start_random_offset', 0) > 0 and adjusted_start:
                    try:
                        start_time = datetime.strptime(adjusted_start, "%I:%M %p")
                        start_time += timedelta(minutes=schedule['start_random_offset'])
                        adjusted_start = start_time.strftime("%I:%M %p")
                    except Exception:
                        adjusted_start = schedule['start']

                # Check if we're within the scheduled period
                if not check_schedule(schedule['days'], adjusted_start, schedule['end']):
                    _off_run_count = run_counter.get_run_count(account_name)
                    _off_smax = schedule.get('max', 0) or 0
                    _off_run_info = f"[{_off_run_count}/{int(_off_smax)}]" if _off_smax > 0 else f"[{_off_run_count}]"
                    status_store.update(account_name, status="off-schedule", next_run="—", run_info=_off_run_info)
                    continue

                # Check if max runs reached for today
                schedule_max = schedule.get('max', 0)
                current_run_count = run_counter.get_run_count(account_name)
                max_runs_reached = (schedule_max > 0 and current_run_count >= schedule_max)

                # Check if it's time to run this account
                should_run = False
                time_until_next = None

                if max_runs_reached:
                    should_run = False
                    time_until_next = None
                else:
                    if next_run_time is None:
                        if last_run is None:
                            next_run_time = current_time
                        else:
                            base_delay = delay_config.get('base', 60.0)
                            random_delay = delay_config.get('random', 0.0)
                            delay_minutes = base_delay + random.uniform(0, random_delay)
                            next_run_time = last_run + timedelta(minutes=delay_minutes)
                        account_next_run[account_name] = next_run_time

                    should_run = current_time >= next_run_time
                    time_until_next = next_run_time - current_time

                # Show account status / trigger run
                if should_run:
                    run_count = run_counter.get_run_count(account_name)
                    next_run = run_count + 1
                    run_info = f"[{next_run}/{schedule_max}]" if schedule_max > 0 else f"[{next_run}]"
                    console.print(f"[bot]: {account_name} - Triggering to ACTIVE state - run {run_info}")
                    console.print("-" * 60)
                    status_store.update(account_name, status="running", next_run="—", run_info=run_info)

                    # Get or create thread on-demand
                    account_idx = account_thread_index.get(account_name)
                    if account_idx is None:
                        event = threading.Event()
                        event.set()
                        account_idx = len(threads_active)
                        permanent_idx = account_idx
                        t = threading.Thread(target=accountSession,
                                            args=(account_name, account_id, account_idx, threads_active, stop_flag, apiClient, permanent_idx, console))
                        threads_active.append(event)
                        threads.append(t)
                        started_accounts.append(account_name)
                        account_thread_index[account_name] = account_idx
                        t.start()
                        while threads_active[account_idx].is_set():
                            time.sleep(1)

                    # Send running heartbeat before session starts
                    _send_hb("running", account_name)

                    # Set account to active
                    threads_active[account_idx].set()

                    # Wait for account to complete and return to idle
                    while threads_active[account_idx].is_set():
                        time.sleep(1)

                    # Update last run time and increment run counter
                    run_finished_time = datetime.now().astimezone()
                    account_last_run[account_name] = run_finished_time
                    new_run_count = run_counter.increment_run_count(account_name)
                    run_counter.set_last_run_time(account_name, run_finished_time)

                    # Set a stable next_run_time
                    delay_config = account_schedules.get(account_name, {}).get('delay', {'base': 60.0, 'random': 0.0})
                    if isinstance(delay_config, dict):
                        base_delay = delay_config.get('base', 60.0)
                        random_delay = delay_config.get('random', 0.0)
                        delay_minutes = base_delay + random.uniform(0, random_delay)
                    else:
                        delay_minutes = float(delay_config)

                    account_next_run[account_name] = run_finished_time + timedelta(minutes=delay_minutes)

                    schedule = account_schedules.get(account_name, {})
                    schedule_max = schedule.get('max', 0)

                    run_info_done = f"[{new_run_count}/{schedule_max}]" if schedule_max > 0 else f"[{new_run_count}]"
                    console.print(f"- [{account_name}]: [summary] run {run_info_done} - DONE")
                    console.print("-" * 60)
                    next_run_str = account_next_run[account_name].strftime("%I:%M %p")
                    status_store.update(account_name, status="idle", next_run=next_run_str, last_action="session complete", run_info=run_info_done)
                elif max_runs_reached:
                    run_count = run_counter.get_run_count(account_name)
                    _max_run_info = f"[{run_count}/{int(schedule_max)}]" if schedule_max > 0 else f"[{run_count}]"
                    status_store.update(account_name, status="max runs", next_run="—", run_info=_max_run_info)
                else:
                    next_run_str = account_next_run[account_name].strftime("%I:%M %p") if account_next_run.get(account_name) else "—"
                    run_count = run_counter.get_run_count(account_name)
                    schedule_max = account_schedules.get(account_name, {}).get('max', 0) or 0
                    run_info = f"[{run_count}/{int(schedule_max)}]" if schedule_max > 0 else f"[{run_count}]"
                    status_store.update(account_name, status="waiting", next_run=next_run_str, run_info=run_info)
                    _any_account_waiting = True

            # Send heartbeat — determine overall client status
            if _any_account_waiting:
                _hb_status, _hb_account = "delay", None
            else:
                _hb_status, _hb_account = "idle", None
            _send_hb(_hb_status, _hb_account)

            if sleep_with_interrupt_check(bot_idle_delay, stop_flag, console=console):
                return

    app = BurnBotApp(BOT_VERSION, _sg, _client_name, _bot_loop, stop_flag)
    status_store.set_app(app)
    app.run()

except KeyboardInterrupt:
    print()
    _beep('shutdown')
    print("Stopping all sessions...")

    stop_flag.set()

    for i in range(len(threads_active)):
        if threads_active[i]:
            threads_active[i].clear()

    print("Waiting for all threads to finish...")
    print("(Press Ctrl+C again to force exit)")

    try:
        for i, t in enumerate(threads):
            if t and t.is_alive():
                account_name = started_accounts[i] if i < len(started_accounts) else f"thread-{i}"
                print(f"Waiting for {account_name} thread...")
                try:
                    t.join(timeout=10)
                except Exception:
                    pass
    except KeyboardInterrupt:
        print()
        print("Force exit requested - threads may not have completed cleanup")

    close_browser_exit = CONFIG.getboolean('bot_settings', 'close_browser_exit', fallback=True)

    print("=" * 60)
    print("[bot]: All threads finished.")

    if close_browser_exit:
        print("[bot]: Browsers will close on exit.")
    else:
        print("[bot]: Browsers left open.")
        print()
        print("** Close this terminal window to keep browsers running **")
        print("   (Script will wait here indefinitely)")
        print()
        while True:
            time.sleep(3600)
