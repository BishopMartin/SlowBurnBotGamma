# burnBot_notifications.py
# Sends notifications via the backend (POST /bot/notify). Credentials live
# server-side; this module just describes the event to send.

import builtins

from burnBot_client_log import client_log_line


def send_admin_notification(account, message, subject_prefix="Alert", sms_summary=None, subject_override=None, apiClient=None, account_id=None, _print=None):
    """
    Send a notification to the admin using prefs from /bot/config and
    server-side dispatch via /bot/notify.
    Returns True if at least one channel was sent successfully.
    """
    if _print is None:
        _print = builtins.print
    try:
        from burnBot_accountSession_setup import is_bot_debug_enabled

        user_config = apiClient.get_user_config() if apiClient else None
        if not user_config:
            _print(client_log_line(account, "notify", "ERROR: Could not fetch notification config from API"))
            return False

        notices_type = (user_config.get('notices_type') or 'none').strip().lower()
        phone = user_config.get('notify_phone') or ''
        email = user_config.get('notify_email') or ''

        if is_bot_debug_enabled():
            redacted_phone = (phone[:3] + "...") if phone else ""
            _print(client_log_line(account, "notify", f"Type: {notices_type}, Phone: {redacted_phone}, Email: {email}"))

        if notices_type == 'none':
            if is_bot_debug_enabled():
                _print(client_log_line(account, "notify", "Notifications disabled (type=none)"))
            return False

        subject = subject_override or f"SlowBurnBot {subject_prefix} - {account}"
        return _dispatch(account, notices_type, email, phone, subject, message, sms_summary, apiClient, account_id=account_id, _print=_print)

    except Exception as e:
        _print(client_log_line(account, "notify", f"Error sending notification: {e}"))
        return False


def _dispatch(account, notices_type, email, phone, subject, message, sms_summary, apiClient, account_id=None, _print=None):
    """Send to the configured channels via the backend. Returns True on any success."""
    if _print is None:
        _print = builtins.print

    # Runtime notify toggle — user can mute via /settings in the terminal panel
    try:
        import burnBot_status as _ss
        if not _ss.is_notify_enabled():
            _print(client_log_line(account, "notify", "suppressed (disabled at runtime)"))
            return False
    except Exception:
        pass

    try:
        from burnBot_accountSession_setup import is_bot_debug_enabled
    except Exception:
        def is_bot_debug_enabled():
            return False

    if apiClient is None:
        _print(client_log_line(account, "notify", "ERROR: no apiClient"))
        return False

    success = False

    if notices_type in ('text', 'both'):
        if not phone:
            _print(client_log_line(account, "notify", "ERROR: notification phone not set"))
            if account_id:
                apiClient.log_error(account_id, "Notification SMS failed: phone not set")
        else:
            sms_msg = sms_summary if sms_summary else message
            if len(sms_msg) > 160:
                sms_msg = sms_msg[:157] + "..."
            if apiClient.notify("sms", phone, sms_msg):
                _print(client_log_line(account, "notify", "SMS sent"))
                success = True
            else:
                _print(client_log_line(account, "notify", "ERROR: SMS failed to send"))
                if account_id:
                    apiClient.log_error(account_id, "Notification SMS failed to send")

    if notices_type in ('email', 'both'):
        if not email:
            _print(client_log_line(account, "notify", "ERROR: notification email not set"))
            if account_id:
                apiClient.log_error(account_id, "Notification email failed: email not set")
        else:
            if apiClient.notify("email", email, message, subject=subject):
                _print(client_log_line(account, "notify", "Email sent"))
                success = True
            else:
                _print(client_log_line(account, "notify", "ERROR: Email failed to send"))
                if account_id:
                    apiClient.log_error(account_id, "Notification email failed to send")

    return success


def send_login_failure_alert(account, error_message, run_count=0, max_runs=0, apiClient=None, account_id=None, _print=None):
    """Send an alert for a login failure using login-specific overrides."""
    if _print is None:
        _print = builtins.print
    try:
        user_config = apiClient.get_user_config() if apiClient else None
        if not user_config or not user_config.get('notices_login', True):
            return

        login_type = (user_config.get('login_notices_type') or user_config.get('notices_type') or 'none').strip().lower()
        login_email = user_config.get('login_notify_email') or user_config.get('notify_email') or ''
        login_phone = user_config.get('login_notify_phone') or user_config.get('notify_phone') or ''

        if login_type == 'none':
            return

        run_info = f"run {run_count}/{max_runs}" if max_runs > 0 else f"run {run_count}"
        formatted_message = f"Login Error ({run_info})\n\nAccount: {account}\nError: {error_message}"
        sms_summary = f"{account} - LOGIN FAILED\n{error_message}\n{run_info}"
        subject = f"SlowBurnBot Login Error - {account}"
        _dispatch(account, login_type, login_email, login_phone, subject, formatted_message, sms_summary, apiClient, account_id=account_id, _print=_print)
    except Exception as e:
        _print(client_log_line(account, "notify", f"Failed to send login failure alert: {e}"))


def send_captcha_challenge_alert(account, novnc_url, run_count=0, max_runs=0, apiClient=None, account_id=None, _print=None):
    """Send an action-required alert when Instagram serves a CAPTCHA challenge during login."""
    if _print is None:
        _print = builtins.print
    try:
        user_config = apiClient.get_user_config() if apiClient else None
        if not user_config or not user_config.get('notices_login', True):
            return

        login_type = (user_config.get('login_notices_type') or user_config.get('notices_type') or 'none').strip().lower()
        login_email = user_config.get('login_notify_email') or user_config.get('notify_email') or ''
        login_phone = user_config.get('login_notify_phone') or user_config.get('notify_phone') or ''

        if login_type == 'none':
            return

        run_info = f"run {run_count}/{max_runs}" if max_runs > 0 else f"run {run_count}"
        body = (
            f"CAPTCHA Challenge — Action Required ({run_info})\n\n"
            f"Account: {account}\n\n"
            f"Instagram is showing a CAPTCHA challenge. Open the link below in your browser "
            f"to view and solve it, then type 'done' in the bot terminal.\n\n"
            f"Browser: {novnc_url}"
        )
        sms_summary = f"{account} - CAPTCHA REQUIRED\nOpen {novnc_url} to solve"
        subject = f"SlowBurnBot CAPTCHA Challenge - {account}"
        _dispatch(account, login_type, login_email, login_phone, subject, body, sms_summary, apiClient, account_id=account_id, _print=_print)
    except Exception as e:
        _print(client_log_line(account, "notify", f"Failed to send CAPTCHA alert: {e}"))


def send_session_complete_notification(account, start_time, end_time,
                                       action1_type, action1_count, action1_target,
                                       action2_type, action2_count, action2_target,
                                       action3_type, action3_count, action3_target,
                                       action4_type, action4_count, action4_target,
                                       run_count=0,
                                       max_runs=0,
                                       error_log="",
                                       apiClient=None,
                                       account_id=None,
                                       _print=None):
    """Send a session-complete notification when enabled in user config."""
    if _print is None:
        _print = builtins.print
    try:
        from burnBot_accountSession_setup import is_bot_debug_enabled
    except Exception:
        def is_bot_debug_enabled():
            return False

    try:
        def _fmt_action_count_first(action_type, action_target, action_count):
            if not action_type:
                return None
            try:
                n = int(action_count)
            except Exception:
                n = 0
            label = f"{action_type}[{action_target}]" if action_target else str(action_type)
            return f"[{n:02d}] {label}"

        user_config = apiClient.get_user_config() if apiClient else None
        if not user_config:
            _print(client_log_line(account, "notify", "Could not fetch config from API, skipping session notification"))
            return

        if not bool(user_config.get('notices_session', True)):
            return

        duration = end_time - start_time
        duration_minutes = int(duration.total_seconds() / 60)
        duration_seconds = int(duration.total_seconds() % 60)

        actions = []
        if action1_type and action1_count > 0:
            actions.append(f"{action1_type}: {action1_count}")
        if action2_type and action2_count > 0:
            actions.append(f"{action2_type}: {action2_count}")
        if action3_type and action3_count > 0:
            actions.append(f"{action3_type}: {action3_count}")
        if action4_type and action4_count > 0:
            actions.append(f"{action4_type}: {action4_count}")

        start_str = start_time.strftime("%I:%M %p")
        end_str = end_time.strftime("%I:%M %p")
        run_info = f"{run_count}/{max_runs}" if max_runs > 0 else f"{run_count}"
        duration_str = f"{duration_minutes:02d}:{duration_seconds:02d}"

        actions_detail = []
        for t, c, tgt in [
            (action1_type, action1_count, action1_target),
            (action2_type, action2_count, action2_target),
            (action3_type, action3_count, action3_target),
            (action4_type, action4_count, action4_target),
        ]:
            formatted = _fmt_action_count_first(t, tgt, c)
            if formatted is not None:
                actions_detail.append(formatted)

        actions_detail_str = "\n".join(actions_detail) if actions_detail else "no actions"

        subject_override = f"SlowBurnBot {account} [{run_info}]"
        message = (
            f"{account} [{run_info}]\n"
            f"{actions_detail_str}\n"
            f"{start_str} - {end_str} [{duration_str}]"
        )
        if error_log:
            message += f"\n{error_log}"

        sms_actions = []
        for t, c, tgt in [
            (action1_type, action1_count, action1_target),
            (action2_type, action2_count, action2_target),
            (action3_type, action3_count, action3_target),
            (action4_type, action4_count, action4_target),
        ]:
            formatted = _fmt_action_count_first(t, tgt, c)
            if formatted is not None:
                sms_actions.append(formatted)

        sms_actions_str = "\n".join(sms_actions) if sms_actions else "no actions"
        sms_summary = f"{account} [{run_info}]\n{sms_actions_str}\n{start_str}-{end_str} [{duration_str}]"
        if error_log:
            sms_summary += f"\n{error_log}"

        send_admin_notification(account, message, subject_prefix="Session Complete", sms_summary=sms_summary, subject_override=subject_override, apiClient=apiClient, account_id=account_id, _print=_print)

    except Exception as e:
        _print(client_log_line(account, "notify", f"Failed to send session complete notification: {e}"))
