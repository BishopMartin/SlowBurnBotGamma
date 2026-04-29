import time
import random
import builtins
from datetime import datetime
from burnBot_config import CONFIG
from burnBot_accountSession_setup import create_driver, is_bot_debug_enabled
from burnBot_login import handle_account_login
from burnBot_utils import check_schedule, process_exception, retry_on_connection_error
from burnBot_notifications import send_login_failure_alert, send_session_complete_notification
from burnBot_likePostsHome import do_like_posts_home
from burnBot_likePostsTopic import do_like_posts_topic
from burnBot_unfollowDatabase import do_unfollow_database
from burnBot_followSuggested import do_follow_suggested
from burnBot_followGroup import do_follow_group
from burnBot_randomActions import do_random_action
import burnBot_status as status_store

# Global dictionary to store driver instances
drivers = {}


def _parse_actions(settings):
    """Parse the actions list from API settings into a flat structure."""
    actions_list = settings.get("actions") or []
    slots = []
    for i in range(4):
        if i < len(actions_list) and actions_list[i]:
            a = actions_list[i]
            slots.append({
                'enabled': bool(a.get('enabled', False)),
                'type': str(a.get('type', '')).strip().lower(),
                'target': str(a.get('target', '')).strip().lower(),
                'fixed_count': int(a.get('fixed_count', 0) or 0),
                'variable_count': int(a.get('variable_count', 0) or 0),
            })
        else:
            slots.append({
                'enabled': False, 'type': '', 'target': '',
                'fixed_count': 0, 'variable_count': 0,
            })
    return slots


def accountSession(account, account_id, idx, threads_active, stop_flag, apiClient, permanent_idx=None, console=None):
    """
    Individual account session handler.
    Manages browser creation and bot script execution for a single account.

    Args:
        account: Account username/identifier
        account_id: UUID string from the API
        idx: Thread index in threads_active list
        threads_active: List of threading.Event objects for state control
        stop_flag: Threading event to signal shutdown
        apiClient: ApiClient instance for API access
        permanent_idx: Optional permanent index for consistent port assignment
        console: rich.Console instance for thread-safe output (optional)
    """
    global drivers
    _print = console.print if console else builtins.print

    time.sleep(1)
    _print(f"- [{account}]: [setup] start thread..")

    # User agent from local config
    accountAgent = CONFIG.get('bot_settings', 'system_user_agent', fallback='').strip()
    if len(accountAgent) >= 2 and ((accountAgent[0] == accountAgent[-1]) and accountAgent[0] in ("'", '"')):
        accountAgent = accountAgent[1:-1].strip()

    # Fetch initial settings from API
    settings = apiClient.get_account_settings(account_id)
    if not settings:
        _print(f"- [{account}]: [setup] ERROR: Could not fetch settings from API")
        threads_active[idx].clear()
        return

    # Parse schedule from settings
    scheduleDays = settings.get("schedule_days") or ""
    scheduleStart = settings.get("schedule_start") or ""
    scheduleEnd = settings.get("schedule_end") or ""
    scheduleMax = int(settings.get("max_runs_per_day", 0) or 0)

    # Parse actions
    action_slots = _parse_actions(settings)

    # Other settings
    unfollow_days = int(settings.get("unfollow_days", 30) or 30)
    action_topics = settings.get("topics") or ""

    # Account group / target accounts for follow[group] action
    account_list_tab = settings.get("account_list_tab") or ""

    driver = None

    # Signal initial setup complete
    threads_active[idx].clear()
    _print(f"- [{account}]: [setup] setup complete and idle")
    status_store.update(account, status="idle", last_action="—")

    # Main loop: Idle <-> Active
    while not stop_flag.is_set():
        if threads_active[idx].is_set():
            # ACTIVE STATE
            # ========================================

            # Open browser for this session
            account_idx_for_port = permanent_idx if permanent_idx is not None else idx
            if driver is not None:
                try:
                    driver.current_url  # quick connectivity check
                    drivers[account] = driver
                    if is_bot_debug_enabled():
                        _print(f"- [{account}]: reusing existing browser session")
                except Exception:
                    driver = None

            if driver is None:
                try:
                    driver = create_driver(account, accountAgent, account_idx=account_idx_for_port)
                    drivers[account] = driver
                    if is_bot_debug_enabled():
                        _print(f"- [{account}]: browser opened for session")
                except Exception as driver_error:
                    _print(f"- [{account}]: ERROR: Failed to create Chrome driver: {driver_error}")
                    apiClient.log_error(account_id, f"Chrome driver creation failed: {driver_error}")
                    threads_active[idx].clear()
                    continue

            if driver is None:
                _print(f"- [{account}]: ERROR: create_driver returned None - skipping session")
                apiClient.log_error(account_id, "Chrome driver creation returned None")
                threads_active[idx].clear()
                continue

            # Re-read settings from API on each session (cached, so fast if unchanged)
            try:
                apiClient.invalidate_settings_cache(account_id)
                fresh_settings = apiClient.get_account_settings(account_id)
                if fresh_settings:
                    settings = fresh_settings
                    scheduleDays = settings.get("schedule_days") or ""
                    scheduleStart = settings.get("schedule_start") or ""
                    scheduleEnd = settings.get("schedule_end") or ""
                    scheduleMax = int(settings.get("max_runs_per_day", 0) or 0)
                    action_slots = _parse_actions(settings)
                    unfollow_days = int(settings.get("unfollow_days", 30) or 30)
                    action_topics = settings.get("topics") or ""
                    account_list_tab = settings.get("account_list_tab") or ""

                    if is_bot_debug_enabled():
                        _print(f"- [{account}]: Re-read settings from API")
            except Exception as e:
                if is_bot_debug_enabled():
                    _print(f"- [{account}]: Error re-reading settings, using cached: {e}")

            # Track session start time
            session_start_time = datetime.now().astimezone()

            # Initialize action counts
            action_counts = [0, 0, 0, 0]

            # Check schedule before attempting login
            if not check_schedule(scheduleDays, scheduleStart, scheduleEnd):
                _print(f"- [{account}]: Skipping - outside scheduled time/day")
                session_end_time = datetime.now().astimezone()
                try:
                    run_seq = apiClient.get_run_count(account_id) + 1
                    apiClient.log_session_run(
                        account_id, session_start_time, session_end_time,
                        "", 0, "", 0, "", 0, "", 0, "", run_sequence=run_seq
                    )
                except Exception as e:
                    _print(f"- [{account}]: Warning - failed to log skipped session: {e}")
                threads_active[idx].clear()
                continue

            # Check max runs
            if scheduleMax > 0:
                try:
                    current_run_count = apiClient.get_run_count(account_id)
                except Exception as e:
                    _print(f"- [{account}]: Error reading run count, returning to IDLE: {e}")
                    threads_active[idx].clear()
                    continue
                if current_run_count >= scheduleMax:
                    _print(f"- [{account}]: Skipping - max runs per day reached ({current_run_count}/{scheduleMax})")
                    threads_active[idx].clear()
                    continue

            session_already_handled = False
            actions_run = 0
            moduleErrorsLog = ""

            try:
                if stop_flag.is_set():
                    _print(f"- [{account}]: Shutdown requested, skipping login and bot script")
                    threads_active[idx].clear()
                    break

                # Get IG password from API
                accountPass = apiClient.get_ig_password(account_id) or ""

                # CHECK LOGIN / ACCOUNT STATUS
                login_success, current_user, loginFailureExit, login_attempts, verification_requested = handle_account_login(
                    driver, account, accountPass, apiClient
                )

                if loginFailureExit:
                    session_end_time = datetime.now().astimezone()
                    if verification_requested:
                        error_msg = "[login failure] - requesting code"
                    else:
                        error_msg = f"[login failure] - {login_attempts} attempt(s) failed"

                    try:
                        run_seq = apiClient.get_run_count(account_id) + 1
                        apiClient.log_session_run(
                            account_id, session_start_time, session_end_time,
                            "", 0, "", 0, "", 0, "", 0,
                            error_msg, run_sequence=run_seq
                        )
                        run_count = run_seq
                        max_runs = scheduleMax
                    except Exception as e:
                        _print(f"- [{account}]: Warning - failed to log login failure session: {e}")
                        run_count, max_runs = 1, scheduleMax

                    try:
                        send_login_failure_alert(account, error_msg, run_count, max_runs, apiClient=apiClient, account_id=account_id, _print=_print)
                    except Exception as notif_error:
                        _print(f"- [{account}]: Warning - notification failed: {notif_error}")

                    threads_active[idx].clear()
                    session_already_handled = True
                    run_info = f"[{run_count}/{max_runs}]" if max_runs > 0 else f"[{run_count}]"
                    _print(f"- [{account}]: returning to IDLE state due to login failure - run {run_info}")
                    status_store.update(account, status="idle", last_action="login failure")
                    continue

                if not loginFailureExit:
                    # RUN BOT SCRIPT
                    try:
                        main_window = driver.current_window_handle
                        if is_bot_debug_enabled():
                            _print(f"- [{account}]: Ready to execute actions")
                    except Exception:
                        main_window = None

                    # Process Actions
                    _action_slots_tuples = [
                        (i + 1, s['enabled'], s['type'], s['target'], s['fixed_count'], s['variable_count'])
                        for i, s in enumerate(action_slots)
                    ]

                    if settings.get("actions_random_order"):
                        random.shuffle(_action_slots_tuples)

                    for _slot_idx, (_slot_num, _enabled, _act_type, _act_target, _fixed, _variable) in enumerate(_action_slots_tuples):
                        _count = 0

                        if _enabled and _act_type:
                            _total = _fixed + random.randint(0, _variable)
                            _print(f"- [{account}]: [action {_slot_num}][enabled] -  [{_act_type}][{_act_target}][{_total}]")
                            status_store.update(account, status="running", last_action=f"{_act_type} · {_act_target}")

                            try:
                                if _act_type == "like" and _act_target in ["home", "homepage posts", "post[homepage]", "posts [homepage]"]:
                                    actions_run += 1
                                    _count, _errs = do_like_posts_home(driver, account, _total, apiClient, account_id, _print=_print)
                                    if _errs:
                                        moduleErrorsLog += _errs

                                elif _act_type == "like" and _act_target in ["post[topics]", "posts [topics]"]:
                                    _topics = action_topics
                                    if _topics:
                                        actions_run += 1
                                        _count, _errs = do_like_posts_topic(driver, account, _total, apiClient, account_id, _topics, _print=_print)
                                        if _errs:
                                            moduleErrorsLog += _errs
                                    else:
                                        _print(f"- [{account}]: [action {_slot_num}] - [{_act_type}][{_act_target}] - ERROR: No topics specified")

                                elif _act_type == "follow" and _act_target in ["suggested", "home", "homepage", "suggested users"]:
                                    actions_run += 1
                                    _count, _errs = do_follow_suggested(driver, account, _total, apiClient, account_id, _print=_print)
                                    if _errs:
                                        moduleErrorsLog += _errs

                                elif _act_type == "follow" and _act_target in ["followers[group]", "following[group]", "account list [followers]", "account list [following]"]:
                                    _target_accounts = account_list_tab
                                    if _target_accounts:
                                        actions_run += 1
                                        _count, _errs = do_follow_group(
                                            driver, account, _total, apiClient, account_id,
                                            _act_target, _target_accounts, _print=_print
                                        )
                                        if _errs:
                                            moduleErrorsLog += _errs
                                    else:
                                        _print(f"- [{account}]: [action {_slot_num}] - [{_act_type}][{_act_target}] - ERROR: No target accounts specified")

                                elif _act_type == "unfollow" and _act_target in ["database", "previous follows"]:
                                    actions_run += 1
                                    _count, _errs = do_unfollow_database(driver, account, _total, apiClient, account_id, unfollow_days, _print=_print)
                                    if _errs:
                                        moduleErrorsLog += _errs

                                else:
                                    if is_bot_debug_enabled():
                                        _print(f"- [{account}]: [action {_slot_num}] ({_act_type}/{_act_target}) is a placeholder")
                                    actions_run += 1

                            except Exception as action_error:
                                error_msg = process_exception(True, f"Action {_slot_num} failed: {action_error}", True, False)
                                apiClient.log_error(account_id, error_msg)
                                _count = 0

                        elif _enabled:
                            _print(f"- [{account}]: [action {_slot_num}][enabled] -  [no type]")
                        else:
                            _display = _act_type if _act_type else "no type"
                            _print(f"- [{account}]: [action {_slot_num}][disabled] -  [{_display}]")

                        action_counts[_slot_idx] = _count

                        # Random action between slots
                        _remaining = _action_slots_tuples[_slot_idx + 1:]
                        if any(_rem_en and _rem_ty for _, _rem_en, _rem_ty, _, _, _ in _remaining):
                            try:
                                do_random_action(driver, account)
                            except Exception:
                                pass

            except Exception as e:
                error_msg = f"ERROR in active state: {e}"
                _print(f"- [{account}]: {error_msg}")
                apiClient.log_error(account_id, error_msg)

            finally:
                if not session_already_handled:
                    session_end_time = datetime.now().astimezone()
                    run_count = 1
                    max_runs = scheduleMax
                    try:
                        run_seq = apiClient.get_run_count(account_id) + 1
                        apiClient.log_session_run(
                            account_id, session_start_time, session_end_time,
                            action_slots[0]['type'], action_counts[0],
                            action_slots[1]['type'], action_counts[1],
                            action_slots[2]['type'], action_counts[2],
                            action_slots[3]['type'], action_counts[3],
                            moduleErrorsLog.strip(),
                            run_sequence=run_seq
                        )
                        run_count = run_seq
                    except Exception as log_error:
                        _print(f"- [{account}]: ERROR in log_session_run: {log_error}")
                        error_details = process_exception(printError=True, noteError="log_session_run failed", logError=True, debugError=False)
                        if error_details:
                            _print(f"- [{account}]: {error_details.strip()}")

                    try:
                        send_session_complete_notification(
                            account,
                            session_start_time,
                            session_end_time,
                            action_slots[0]['type'], action_counts[0], action_slots[0]['target'],
                            action_slots[1]['type'], action_counts[1], action_slots[1]['target'],
                            action_slots[2]['type'], action_counts[2], action_slots[2]['target'],
                            action_slots[3]['type'], action_counts[3], action_slots[3]['target'],
                            run_count,
                            max_runs,
                            moduleErrorsLog.strip(),
                            apiClient=apiClient,
                            account_id=account_id,
                            _print=_print,
                        )
                    except Exception as notif_error:
                        _print(f"- [{account}]: Warning - session notification failed: {notif_error}")
                        process_exception(printError=False, noteError="session notification failed", logError=False, debugError=False)

                    threads_active[idx].clear()
                    run_info = f"[{run_count}/{max_runs}]" if max_runs > 0 else f"[{run_count}]"
                    _print(f"- [{account}]: [summary] run {run_info} - {actions_run} action(s) executed")
                    status_store.update(account, status="idle", last_action="session complete")

                # Close or keep browser based on config
                close_browser_session = CONFIG.getboolean('bot_settings', 'close_browser_session', fallback=True)
                if close_browser_session:
                    if driver is not None:
                        try:
                            driver.quit()
                        except Exception:
                            pass
                        try:
                            from burnBot_accountSession_setup import build_user_data_dir, kill_chrome_processes_for_profile
                            chrome_user_data_dir = build_user_data_dir(account)
                            time.sleep(0.5)
                            kill_chrome_processes_for_profile(chrome_user_data_dir, account)
                            if is_bot_debug_enabled():
                                _print(f"- [{account}]: browser closed after session")
                        except Exception:
                            pass
                    drivers.pop(account, None)
                    driver = None

        else:
            # IDLE STATE
            time.sleep(5)

    # Cleanup on exit
    _print(f"- [{account}]: shutting down...")

    close_browser_exit = True
    if CONFIG.has_section('bot_settings'):
        close_browser_exit = CONFIG.getboolean('bot_settings', 'close_browser_exit', fallback=True)

    if driver is not None:
        try:
            if close_browser_exit:
                driver_still_connected = False
                try:
                    window_handles = driver.window_handles
                    driver_still_connected = True
                    if window_handles:
                        try:
                            main_window = driver.current_window_handle
                        except Exception:
                            main_window = window_handles[0] if window_handles else None

                        extra_windows = [h for h in window_handles if h != main_window]
                        if extra_windows:
                            _print(f"- [{account}]: Closing {len(extra_windows)} extra browser window(s)...")
                            for handle in extra_windows:
                                try:
                                    driver.switch_to.window(handle)
                                    driver.close()
                                except Exception:
                                    pass
                            if main_window:
                                try:
                                    driver.switch_to.window(main_window)
                                except Exception:
                                    pass
                            time.sleep(0.5)
                except Exception:
                    driver_still_connected = False
                    _print(f"- [{account}]: Driver connection already lost, will kill Chrome processes directly")

                if driver_still_connected:
                    try:
                        driver.quit()
                    except Exception:
                        pass

                try:
                    from burnBot_accountSession_setup import build_user_data_dir, kill_chrome_processes_for_profile
                    chrome_user_data_dir = build_user_data_dir(account)
                    time.sleep(0.5)
                    kill_chrome_processes_for_profile(chrome_user_data_dir, account)
                    _print(f"- [{account}]: thread exiting, browser closed.")
                except Exception as e:
                    _print(f"- [{account}]: Error killing Chrome processes: {e}")
            else:
                try:
                    _print(f"- [{account}]: thread exiting, browser ready.")
                except Exception as e:
                    _print(f"- [{account}]: Error during disconnect: {e}")
        except Exception as e:
            _print(f"- [{account}]: Error during cleanup: {e}")
