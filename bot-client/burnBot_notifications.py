# burnBot_notifications.py
# Handles sending notifications via SMS and/or email

import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_sms_textbelt(phone, message, api_key):
    """
    Send SMS using TextBelt API
    
    Args:
        phone: Phone number (10-digit or with country code)
        message: Message text
        api_key: TextBelt API key
        
    Returns:
        bool: True if successful, False otherwise
    """
    url = "https://textbelt.com/text"
    
    payload = {
        "phone": phone,
        "message": message,
        "key": api_key
    }
    
    try:
        response = requests.post(url, data=payload, timeout=10)
        result = response.json()
        
        if result.get("success"):
            return True
        else:
            return False
            
    except Exception as e:
        return False


def send_email_smtp(to_email, subject, message, smtp_server, smtp_port, smtp_user, smtp_password):
    """
    Send email using SMTP
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        message: Email body text
        smtp_server: SMTP server address (e.g., smtp.gmail.com)
        smtp_port: SMTP port (e.g., 587 for TLS)
        smtp_user: SMTP username/login
        smtp_password: SMTP password
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))
        
        # Connect and send with 15 second timeout
        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        return False


def send_admin_notification(account, message, subject_prefix="Alert", sms_summary=None, subject_override=None, apiClient=None):
    """
    Send notification to admin. All config comes from the web app API:
    - User prefs (type, email, phone) from /bot/config
    - SMTP/TextBelt credentials from /bot/notification-credentials

    Args:
        account: Instagram account name
        message: Message to send (can be error or status update)
        subject_prefix: Prefix for email subject (default: "Alert")
        sms_summary: Optional short summary for SMS (default: use first 160 chars of message)
        subject_override: Optional full subject line override
        apiClient: ApiClient instance for fetching config from API

    Returns:
        bool: True if at least one notification was sent successfully
    """
    try:
        from burnBot_accountSession_setup import is_bot_debug_enabled

        # Get notification prefs from API
        user_config = apiClient.get_user_config() if apiClient else None

        if not user_config:
            print(f"- [{account}]: [NOTIFICATION] ERROR: Could not fetch notification config from API")
            return False

        admin_notices_type = (user_config.get('notices_type') or 'none').strip().lower()
        admin_phone = user_config.get('notify_phone') or ''
        admin_email = user_config.get('notify_email') or ''

        if is_bot_debug_enabled():
            print(f"- [{account}]: [NOTIFICATION] Type: {admin_notices_type}, Phone: {admin_phone[:3]}..., Email: {admin_email}")

        if admin_notices_type == 'none':
            if is_bot_debug_enabled():
                print(f"- [{account}]: [NOTIFICATION] Notifications disabled (type=none)")
            return False

        # Get SMTP/TextBelt credentials from API
        notif_creds = apiClient.get_notification_credentials() if apiClient else None

        if not notif_creds:
            print(f"- [{account}]: [NOTIFICATION] ERROR: Could not fetch notification credentials from API")
            return False

        if subject_override:
            subject = subject_override
        else:
            subject = f"SlowBurnBot {subject_prefix} - {account}"

        success = False

        # Send SMS if configured
        if admin_notices_type in ['text', 'both']:
            try:
                textbelt_key = notif_creds.get('textbelt_key') or ''

                if not textbelt_key:
                    print(f"- [{account}]: [NOTIFICATION] ERROR: TextBelt API key not set in admin config")
                    return False

                if not admin_phone:
                    print(f"- [{account}]: [NOTIFICATION] ERROR: notification phone not set in web app config")
                    return False

                sms_message = sms_summary if sms_summary else message
                if len(sms_message) > 160:
                    sms_message = sms_message[:157] + "..."

                if send_sms_textbelt(admin_phone, sms_message, textbelt_key):
                    if is_bot_debug_enabled():
                        print(f"- [{account}]: [NOTIFICATION] SMS sent successfully")
                    success = True
                else:
                    print(f"- [{account}]: [NOTIFICATION] ERROR: SMS failed to send")
                    return False

            except Exception as e:
                print(f"- [{account}]: [NOTIFICATION] ERROR: SMS failed: {e}")
                return False

        # Send email if configured
        if admin_notices_type in ['email', 'both']:
            try:
                smtp_server = notif_creds.get('smtp_server') or ''
                smtp_port = notif_creds.get('smtp_port') or 587
                smtp_user = notif_creds.get('smtp_user') or ''
                smtp_password = notif_creds.get('smtp_password') or ''

                if not admin_email:
                    print(f"- [{account}]: [NOTIFICATION] ERROR: notification email not set in web app config")
                    return False

                if not smtp_server or not smtp_user or not smtp_password:
                    missing = [k for k, v in [('smtp_server', smtp_server), ('smtp_user', smtp_user), ('smtp_password', smtp_password)] if not v]
                    print(f"- [{account}]: [NOTIFICATION] ERROR: Missing SMTP credentials in admin config: {', '.join(missing)}")
                    return False

                if send_email_smtp(admin_email, subject, message, smtp_server, smtp_port, smtp_user, smtp_password):
                    if is_bot_debug_enabled():
                        print(f"- [{account}]: [NOTIFICATION] Email sent successfully")
                    success = True
                else:
                    print(f"- [{account}]: [NOTIFICATION] ERROR: Email failed to send")
                    return False

            except Exception as e:
                print(f"- [{account}]: [NOTIFICATION] ERROR: Email failed: {e}")
                return False

        return success

    except Exception as e:
        print(f"- [{account}]: [NOTIFICATION] Error sending notification: {e}")
        return False


def send_login_failure_alert(account, error_message, run_count=0, max_runs=0, apiClient=None):
    """
    Send alert for login failure

    Args:
        account: Instagram account name
        error_message: Error message from login failure
        run_count: Current run count
        max_runs: Maximum runs per day (0 if unlimited)
        apiClient: ApiClient instance for fetching user config from API
    """
    try:
        run_info = f"run {run_count}/{max_runs}" if max_runs > 0 else f"run {run_count}"
        formatted_message = f"Login Error ({run_info})\n\nAccount: {account}\nError: {error_message}"
        sms_summary = f"{account} - LOGIN FAILED\n{error_message}\n{run_info}"
        send_admin_notification(account, formatted_message, subject_prefix="Login Error", sms_summary=sms_summary, apiClient=apiClient)
    except Exception as e:
        print(f"- [{account}]: [NOTIFICATION] Failed to send login failure alert: {e}")


def send_session_complete_notification(account, start_time, end_time,
                                       action1_type, action1_count, action1_target,
                                       action2_type, action2_count, action2_target,
                                       action3_type, action3_count, action3_target,
                                       action4_type, action4_count, action4_target,
                                       run_count=0,
                                       max_runs=0,
                                       error_log="",
                                       apiClient=None):
    """
    Send notification when session completes successfully

    Args:
        account: Instagram account name
        start_time: Session start datetime
        end_time: Session end datetime
        action1_type: Type of action 1
        action1_count: Count of action 1
        action2_type: Type of action 2
        action2_count: Count of action 2
        action3_type: Type of action 3
        action3_count: Count of action 3
        action4_type: Type of action 4
        action4_count: Count of action 4
        run_count: Current run count
        max_runs: Maximum runs per day (0 if unlimited)
        apiClient: ApiClient instance for fetching user config from API
    """
    from burnBot_accountSession_setup import is_bot_debug_enabled

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

        # Check if session notifications are enabled from web app config
        user_config = apiClient.get_user_config() if apiClient else None

        if not user_config:
            print(f"- [{account}]: [NOTIFICATION] Could not fetch config from API, skipping session notification")
            return

        admin_notices_session = bool(user_config.get('notices_session', True))
        
        if is_bot_debug_enabled():
            print(f"- [{account}]: Checking session notifications (enabled: {admin_notices_session})")
        
        if not admin_notices_session:
            return  # Session notifications disabled
        
        # Calculate duration
        duration = end_time - start_time
        duration_minutes = int(duration.total_seconds() / 60)
        duration_seconds = int(duration.total_seconds() % 60)
        
        # Build actions summary
        actions = []
        if action1_type and action1_count > 0:
            actions.append(f"{action1_type}: {action1_count}")
        if action2_type and action2_count > 0:
            actions.append(f"{action2_type}: {action2_count}")
        if action3_type and action3_count > 0:
            actions.append(f"{action3_type}: {action3_count}")
        if action4_type and action4_count > 0:
            actions.append(f"{action4_type}: {action4_count}")
        
        actions_summary = ", ".join(actions) if actions else "No actions"
        total_actions = action1_count + action2_count + action3_count + action4_count
        
        # Format times
        start_str = start_time.strftime("%I:%M %p")
        end_str = end_time.strftime("%I:%M %p")
        
        # Format run info
        run_info = f"{run_count}/{max_runs}" if max_runs > 0 else f"{run_count}"
        
        # Format duration as MM:SS
        duration_str = f"{duration_minutes:02d}:{duration_seconds:02d}"
        
        # Build detailed actions list for email (show all actions that were attempted, even if count is 0)
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
        
        # Build notification subject/body (full version for email)
        subject_override = f"SlowBurnBot {account} [{run_info}]"
        message = (
            f"{account} [{run_info}]\n"
            f"{actions_detail_str}\n"
            f"{start_str} - {end_str} [{duration_str}]"
        )
        if error_log:
            message += f"\n{error_log}"

        # Build short SMS summary - show all actions in compact format
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
        
        # Put each action on its own line so every one clearly starts with [NN]
        sms_actions_str = "\n".join(sms_actions) if sms_actions else "no actions"
        sms_summary = f"{account} [{run_info}]\n{sms_actions_str}\n{start_str}-{end_str} [{duration_str}]"
        if error_log:
            sms_summary += f"\n{error_log}"
        
        if is_bot_debug_enabled():
            print(f"- [{account}]: Sending session notification...")
        
        # Send notification
        send_admin_notification(account, message, subject_prefix="Session Complete", sms_summary=sms_summary, subject_override=subject_override, apiClient=apiClient)
        
        if is_bot_debug_enabled():
            print(f"- [{account}]: Session notification complete")
        
    except Exception as e:
        # Don't let notification errors break the bot
        print(f"- [{account}]: [NOTIFICATION] Failed to send session complete notification: {e}")
