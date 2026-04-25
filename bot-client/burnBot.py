# burnBot.py

from burnBot_imports import *
from burnBot_config import load_config, CONFIG, resolve_path
from burnBot_utils import close_windows, has_internet_connection, process_exception, delay, check_schedule, consume_connectivity_recovery_notice
from burnBot_accountSession import accountSession
from burnBot_accountSession_setup import is_bot_debug_enabled
from burnBot_apiClient import ApiClient, AuthenticationError, SubscriptionRequiredError
from burnBot_runCounter import RunCounter
from burnBot_version import BOT_VERSION
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


def _api_credentials_from_ini():
    email = CONFIG.get("api_credentials", "email", fallback="").strip()
    password = CONFIG.get("api_credentials", "password", fallback="").strip()
    return email, password


def _try_api_relogin_from_config(client):
    """
    Re-post /auth/jwt/login using [api_credentials] when the keyring JWT is stale.
    JWT access tokens expire (server default 1h); refresh only works while still valid.
    """
    email, password = _api_credentials_from_ini()
    if not email or not password:
        return False
    print("[api]: Session expired — re-authenticating with [api_credentials] from config...")
    ok = client.login(email, password)
    if ok:
        print("[api]: Re-login OK.")
    return bool(ok)


# Load bot_idle_delay for main loop check interval (in minutes, convert to seconds)
bot_idle_delay_minutes = CONFIG.getint('bot_settings', 'bot_idle_delay', fallback=1)
bot_idle_delay = bot_idle_delay_minutes * 60  # Convert to seconds

# Helper function for interruptible sleep
def sleep_with_interrupt_check(seconds, stop_flag, label=None):
    """
    Sleep for specified seconds, checking for keyboard input every 0.5 seconds.
    If label is provided, prints a live count-up line: label [M:SS/M:SS]
    Returns True if interrupted by keyboard, False if sleep completed normally.
    Works on both Windows and Linux/Chromebook.
    """
    import sys

    def _fmt(s):
        s = max(0, int(s))
        return f"{s // 60}:{s % 60:02d}"

    total_str = _fmt(seconds)
    elapsed = 0.0

    def _draw():
        if label:
            sys.stdout.write(f"\r{label} [{_fmt(elapsed)}/{total_str}]   ")
            sys.stdout.flush()

    def _end_line():
        if label:
            sys.stdout.write("\n")
            sys.stdout.flush()

    intervals = int(seconds / 0.5)

    if sys.platform == 'win32':
        import msvcrt
        while msvcrt.kbhit():
            msvcrt.getch()

        for _ in range(intervals):
            if stop_flag.is_set():
                _end_line()
                return True
            _draw()
            if msvcrt.kbhit():
                msvcrt.getch()
                _end_line()
                _beep('keypress')
                print("=" * 60)
                print("Keyboard input detected - initiating graceful shutdown...")
                print("=" * 60)
                return True
            time.sleep(0.5)
            elapsed += 0.5
    else:
        import select
        for _ in range(intervals):
            if stop_flag.is_set():
                _end_line()
                return True
            _draw()
            if select.select([sys.stdin], [], [], 0)[0]:
                _end_line()
                _beep('keypress')
                print("=" * 60)
                print("Keyboard input detected - initiating graceful shutdown...")
                print("=" * 60)
                return True
            time.sleep(0.5)
            elapsed += 0.5

    _end_line()
    return False


# ------------------------------------------------------------------
# Authentication — prompt for login if no stored token
# ------------------------------------------------------------------
if not apiClient.has_token():
    # Try credentials from config first
    cfg_email = CONFIG.get('api_credentials', 'email', fallback='').strip()
    cfg_password = CONFIG.get('api_credentials', 'password', fallback='').strip()

    if cfg_email and cfg_password:
        print("Using credentials from config file...")
        if not apiClient.login(cfg_email, cfg_password):
            print("Config credentials failed. Falling back to manual entry.")
            cfg_email = ''
            cfg_password = ''

    if not apiClient.has_token():
        print("Login required.")
        print("=" * 60)
        email = input("Email: ").strip()
        password = input("Password: ").strip()
        if not apiClient.login(email, password):
            print("Login failed. Exiting.")
            sys.exit(1)

    print("Login successful.")
    print()

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
    print(f"Subscription active (plan: {entitlement.get('plan_tier')})")
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

    print(f"SlowBurnBot - BurnBot Client v {BOT_VERSION}")
    print()
    print("Bot Settings:")
    print("=" * 60)
    time.sleep(_p); print(f"{'local config file:':<{_w}}[{config_file}]")
    time.sleep(_p); print(f"{'api_url:':<{_w}}[{api_url}]")
    time.sleep(_p); print(f"{'client_id:':<{_w}}[{_sg}]")
    time.sleep(_p); print(f"{'system_type:':<{_w}}[{_st}]")
    time.sleep(_p); print(f"{'debug:':<{_w}}[{_dbg}]")
    time.sleep(_p); print(f"{'system_user_agent:':<{_w}}[{_ua}]")
    time.sleep(_p); print(f"{'close_browser_session:':<{_w}}[{_cs}]")
    time.sleep(_p); print(f"{'close_browser_exit:':<{_w}}[{_ce}]")
    time.sleep(_p); print(f"{'bot_idle_delay:':<{_w}}[{_idl}]")
    print()
    print("Session Settings (from web app):")
    print("=" * 60)
    time.sleep(_p); print(f"{'like_suggested:':<{_w}}[{_lks}]")
    time.sleep(_p); print(f"{'like_sponsored:':<{_w}}[{_lkp}]")
    time.sleep(_p); print(f"{'skip_login_check:':<{_w}}[{_skl}]")
    time.sleep(_p); print(f"{'login_tries:':<{_w}}[{_lgt}]")
    print()
    print("Notification Settings (from web app):")
    print("=" * 60)
    time.sleep(_p); print(f"{'notices_type:':<{_w}}[{_ant}]")
    time.sleep(_p); print(f"{'notices_session:':<{_w}}[{_ans}]")
    time.sleep(_p); print(f"{'notify_email:':<{_w}}[{_ane}]")
    time.sleep(_p); print(f"{'notify_phone:':<{_w}}[{_anp}]")
    print()
    _beep('startup')
    time.sleep(2)

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
                    print("[system]: Session expired after re-login. Check [api_credentials] or dashboard.")
                    break
            else:
                print("[system]: Session expired. Set [api_credentials] in burnBot_config.ini or restart and log in.")
                break
        except Exception as e:
            if is_bot_debug_enabled():
                print(f"[system]: Warning - account refresh failed, using cached values: {e}")
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

        print()
        print(f"[{current_time.strftime('%I:%M %p')}] Account Status Check")
        print("=" * 60)

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
                print(f"[bot]: {account_name} - [{skip_msg}]")
                continue

            # Account is active - check schedule and timing
            if account_name not in account_schedules:
                print(f"[bot]: {account_name} - [no schedule]")
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
                print(f"[bot]: {account_name} - [enabled] - outside scheduled time")
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

            # Show account status
            if should_run:
                run_count = run_counter.get_run_count(account_name)
                next_run = run_count + 1
                run_info = f"[{next_run}/{schedule_max}]" if schedule_max > 0 else f"[{next_run}]"
                print(f"[bot]: {account_name} -Triggering to ACTIVE state - run {run_info}")
                print("-" * 60)

                # Get or create thread on-demand
                account_idx = account_thread_index.get(account_name)
                if account_idx is None:
                    event = threading.Event()
                    event.set()
                    account_idx = len(threads_active)
                    permanent_idx = account_idx
                    t = threading.Thread(target=accountSession,
                                        args=(account_name, account_id, account_idx, threads_active, stop_flag, apiClient, permanent_idx))
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
                print(f"- [{account_name}]: [summary] run {run_info_done} - DONE")
                print("-" * 60)
            elif max_runs_reached:
                run_count = run_counter.get_run_count(account_name)
                print(f"[bot]: {account_name} - [max runs reached] [{run_count}/{int(schedule_max)}]")
            else:
                minutes_remaining = max(0, int(math.ceil(time_until_next.total_seconds() / 60)))
                run_count = run_counter.get_run_count(account_name)
                schedule_max = account_schedules.get(account_name, {}).get('max', 0) or 0
                run_info = f"[{run_count}/{int(schedule_max)}]" if schedule_max > 0 else f"[{run_count}]"
                print(f"[bot]: {account_name} - [waiting] {run_info} - {minutes_remaining}m until next run")
                _any_account_waiting = True

        print("=" * 60)

        # Send heartbeat — determine overall client status
        if _any_account_waiting:
            _hb_status, _hb_account = "delay", None
        else:
            _hb_status, _hb_account = "idle", None
        _send_hb(_hb_status, _hb_account)

        _delay_label = f"[{current_time.strftime('%I:%M %p')}] delay:"
        if sleep_with_interrupt_check(bot_idle_delay, stop_flag, label=_delay_label):
            raise KeyboardInterrupt

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
