# burnBot_login.py

from burnBot_imports import *
from burnBot_utils import close_windows, has_internet_connection, process_exception, delay
from burnBot_client_log import client_log_line


def is_bot_debug_enabled():
    """Check if bot_debug is enabled in config"""
    try:
        from burnBot_config import CONFIG
        return CONFIG.getboolean('bot_settings', 'bot_debug', fallback=False)
    except Exception:
        return False


def _find_browser_window_for_driver(driver):
    """Best-effort: pygetwindow window that matches Selenium driver.title (foreground target for ESC)."""
    try:
        import pygetwindow as gw
    except ImportError:
        return None
    try:
        dt = (driver.title or "").strip()
        if dt:
            for w in gw.getAllWindows():
                if not w.title:
                    continue
                if dt == w.title or dt in w.title or w.title in dt:
                    return w
                head = dt.split(" - ")[0].strip()
                if head and head in w.title:
                    return w
        for needle in ("Instagram", "instagram", "Chrome"):
            wins = gw.getWindowsWithTitle(needle)
            if wins:
                return wins[0]
        for w in gw.getAllWindows():
            if w.title and "chrome" in w.title.lower():
                return w
    except Exception:
        pass
    return None


def os_focus_browser_and_press_escape(presses=8, pause=0.48, context_label="", driver=None):
    """
    Activate the Chrome window at the OS level and send Escape via PyAutoGUI.
    Selenium send_keys often fails for Instagram overlays when the browser is not focused.
    """
    try:
        import pyautogui
        import pygetwindow as gw  # noqa: F401 — used via _find_browser_window_for_driver
    except ImportError:
        if is_bot_debug_enabled():
            print(f"-- DEBUG: [{context_label}] pyautogui/pygetwindow missing; OS-level ESC skipped")
        return False

    win = _find_browser_window_for_driver(driver) if driver else None
    if not win:
        try:
            import pygetwindow as gw
            for needle in ("Instagram", "instagram", "Chrome"):
                wins = gw.getWindowsWithTitle(needle)
                if wins:
                    win = wins[0]
                    break
        except Exception:
            pass
    if not win:
        if is_bot_debug_enabled():
            print(f"-- DEBUG: [{context_label}] No window found to activate for OS ESC")
        return False

    try:
        try:
            if win.isMinimized:
                win.restore()
        except Exception:
            pass
        win.activate()
        time.sleep(0.95)
        for _ in range(presses):
            pyautogui.press("esc")
            time.sleep(pause)
        if is_bot_debug_enabled():
            print(
                f"-- DEBUG: [login][escape][os] presses={presses} window={win.title!r} ({context_label})"
            )
        return True
    except Exception as e:
        if is_bot_debug_enabled():
            print(f"-- DEBUG: [{context_label}] OS-level ESC error: {e}")
        return False


def press_escape_to_dismiss_overlays(
    driver,
    presses=4,
    pause=0.45,
    context_label="",
    *,
    os_esc_before=False,
    os_esc_after=False,
    os_presses=3,
):
    """
    Dismiss Instagram account / 'Sign in as' sheets. Too many Escape events (especially OS-level
    PyAutoGUI before AND after Selenium) can reload the page and bring the sheet back — use a
    single modest OS burst when needed (os_esc_before), avoid os_esc_after unless necessary.

    os_presses: PyAutoGUI Escape count when os_esc_before/os_esc_after is True.
    presses: Selenium-side rounds (lighter than hammering OS keys repeatedly).
    """
    prefix = f"[{context_label}] " if context_label else ""
    if os_esc_before and os_presses > 0:
        os_focus_browser_and_press_escape(
            os_presses, pause, context_label=f"{context_label}_os", driver=driver
        )

    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    for i in range(presses):
        try:
            driver.execute_script(
                "var b = document.body; if (b) { b.setAttribute('tabindex','-1'); b.focus(); }"
            )
        except Exception:
            pass
        try:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        except Exception:
            pass
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except Exception:
            pass
        try:
            driver.execute_script(
                """
                (function () {
                  var ev = function (type) {
                    return new KeyboardEvent(type, {
                      key: 'Escape', code: 'Escape', keyCode: 27, which: 27, bubbles: true, cancelable: true
                    });
                  };
                  var t = document.activeElement || document.body;
                  t.dispatchEvent(ev('keydown'));
                  t.dispatchEvent(ev('keyup'));
                })();
                """
            )
        except Exception:
            pass
        time.sleep(pause)

    if os_esc_after and os_presses > 0:
        os_focus_browser_and_press_escape(
            os_presses, pause, context_label=f"{context_label}_os_after", driver=driver
        )

    if presses and is_bot_debug_enabled():
        print(f"-- DEBUG: {prefix}Escape overlay dismissal: {presses} selenium rounds")


def dismiss_browser_dialogs(driver, max_attempts=3, wait_between=0.3):
    """
    Check for and dismiss any browser dialogs (alert/confirm/prompt).
    These dialogs block all Selenium interactions until dismissed.
    
    Args:
        driver: Selenium WebDriver instance
        max_attempts: Maximum number of times to check for dialogs
        wait_between: Seconds to wait between attempts
        
    Returns:
        int: Number of dialogs dismissed
    """
    dialogs_dismissed = 0
    for attempt in range(max_attempts):
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            print(client_log_line(None, "login", f"Browser dialog #{dialogs_dismissed + 1} detected: '{alert_text}' — dismissing…"))
            alert.accept()  # Try accepting instead of dismissing
            dialogs_dismissed += 1
            time.sleep(wait_between)
        except Exception:
            # No alert present
            if dialogs_dismissed > 0:
                time.sleep(0.2)  # Brief pause to ensure dialog is fully gone
            break
    
    if dialogs_dismissed > 0:
        print(client_log_line(None, "login", f"Dismissed {dialogs_dismissed} browser dialog(s)"))
    
    return dialogs_dismissed


INSTAGRAM_ACCOUNTS_LOGIN = "https://www.instagram.com/accounts/login/"


def navigate_to_instagram_login_if_needed(driver, *, long_initial_settle=True):
    """
    Open the credential login URL only when not already there — avoids an extra full
    reload when check_login and do_login run back-to-back on the same tab.
    Returns True if driver.get() was skipped (already on /accounts/login/).
    """
    try:
        u = (driver.current_url or "").lower()
    except Exception:
        u = ""
    if "instagram.com/accounts/login" in u:
        try:
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass
        time.sleep(2.0 if long_initial_settle else 1.0)
        if is_bot_debug_enabled():
            print(client_log_line(None, "login", "already on /accounts/login/ — skipped driver.get()"))
        return True
    driver.get(INSTAGRAM_ACCOUNTS_LOGIN)
    WebDriverWait(driver, 22).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    WebDriverWait(driver, 22).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    time.sleep(5.0 if long_initial_settle else 2.5)
    return False


def submit_instagram_credentials(driver, password_input, log_name="login"):
    """
    Submit the login form. IG often nests the label in a child (e.g. <button><div>Log in</div>),
    so contains(text(),...) on the button fails; prefer real submit buttons + JS click.
    """
    time.sleep(0.45)
    try:
        password_input.send_keys(Keys.TAB)
        time.sleep(0.4)
    except Exception:
        pass
    try:
        WebDriverWait(driver, 12).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button[type='submit']"))
        )
    except Exception:
        pass
    time.sleep(0.35)

    def _disabled(btn):
        try:
            v = btn.get_attribute("disabled")
            return v is not None and str(v).lower() in ("true", "disabled")
        except Exception:
            return False

    try:
        buttons = driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
    except Exception:
        buttons = []
    for btn in buttons:
        try:
            if not btn.is_displayed() or _disabled(btn):
                continue
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'nearest'});", btn
            )
            time.sleep(0.45)
            try:
                WebDriverWait(driver, 10).until(lambda d: btn.is_enabled())
            except Exception:
                pass
            try:
                btn.click()
                if is_bot_debug_enabled():
                    print(client_log_line(log_name, "login", "debug submit: native click (type=submit)"))
                return True
            except Exception:
                driver.execute_script("arguments[0].click();", btn)
                if is_bot_debug_enabled():
                    print(client_log_line(log_name, "login", "debug submit: JS click (type=submit)"))
                return True
        except Exception:
            continue

    tr = "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'"
    xpath_buttons = [
        f"//button[.//span[contains(translate(normalize-space(string(.)), {tr}), 'log in')]]",
        f"//button[contains(translate(normalize-space(string(.)), {tr}), 'log in')]",
        f"//div[@role='button'][.//span[contains(translate(normalize-space(string(.)), {tr}), 'log in')]]",
    ]
    for xp in xpath_buttons:
        try:
            btn = WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.XPATH, xp)))
            if not btn.is_displayed() or _disabled(btn):
                continue
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'nearest'});", btn
            )
            time.sleep(0.4)
            driver.execute_script("arguments[0].click();", btn)
            if is_bot_debug_enabled():
                print(client_log_line(log_name, "login", "debug submit: xpath / role=button"))
            return True
        except Exception:
            continue

    return False


def dismiss_instagram_account_picker(driver, context_label="login", max_passes=4):
    """
    Instagram often shows an account sheet before the password form (e.g. 'Continue as @user',
    'Sign in as', saved session). Click through to manual / credential login when those controls exist.
    Safe no-op when the sheet is not present.
    """
    tr = "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'"
    # Prefer exact labels first (less false positives than substring on huge containers)
    exact_labels = [
        "Use another account",
        "Log in to an existing account",
        "Log in to existing account",
        "Log into another account",
        "Switch accounts",
        "Not you?",
    ]
    substring_hits = [
        "use another account",
        "log in to an existing account",
        "log into another account",
    ]

    def _click_el(el):
        try:
            clickable = driver.execute_script(
                """
                var n = arguments[0];
                for (var i = 0; i < 10 && n; i++) {
                    var role = n.getAttribute && n.getAttribute('role');
                    var tag = n.tagName;
                    if ((tag === 'BUTTON' || tag === 'A' || role === 'button' || role === 'menuitem') && typeof n.click === 'function')
                        return n;
                    n = n.parentElement;
                }
                return arguments[0];
                """,
                el,
            )
            driver.execute_script("arguments[0].click();", clickable)
            return True
        except Exception:
            try:
                el.click()
                return True
            except Exception:
                return False

    clicked_any = False
    for _ in range(max_passes):
        found = False
        for label in exact_labels:
            esc = label.replace("'", "\\'")
            for tag in ("span", "div", "button"):
                xp = (
                    f"//{tag}[normalize-space(.)='{esc}']/ancestor::*["
                    f"@role='button' or self::button or self::a][1]"
                )
                try:
                    els = driver.find_elements(By.XPATH, xp)
                    for el in els:
                        if el.is_displayed() and _click_el(el):
                            print(client_log_line(None, "login", f"{context_label} account picker: clicked {label!r}"))
                            time.sleep(1.6)
                            found = True
                            clicked_any = True
                            break
                    if found:
                        break
                except Exception:
                    continue
            if found:
                break

        if not found:
            for sub in substring_hits:
                xp = (
                    f"//*[self::span or self::div or self::button]"
                    f"[contains(translate(normalize-space(string(.)), {tr}), '{sub}')]"
                )
                try:
                    for el in driver.find_elements(By.XPATH, xp):
                        if not el.is_displayed():
                            continue
                        if _click_el(el):
                            print(client_log_line(None, "login", f"{context_label} account picker: matched {sub!r}"))
                            time.sleep(1.6)
                            found = True
                            clicked_any = True
                            break
                    if found:
                        break
                except Exception:
                    continue

        if not found:
            for xp in (
                "//div[@role='dialog']//*[@aria-label='Close' or @aria-label='close']",
                "//*[@role='dialog']//svg[@aria-label='Close']/ancestor::*[@role='button'][1]",
            ):
                try:
                    for el in driver.find_elements(By.XPATH, xp):
                        if el.is_displayed() and _click_el(el):
                            print(client_log_line(None, "login", f"{context_label} account picker: closed via dialog dismiss control"))
                            time.sleep(1.4)
                            found = True
                            clicked_any = True
                            break
                    if found:
                        break
                except Exception:
                    continue

        if not found:
            break

    # Light Selenium Escape only (OS burst happens in check_login / do_login — avoids double-reload)
    press_escape_to_dismiss_overlays(
        driver, presses=2, pause=0.35, context_label=context_label, os_esc_before=False, os_esc_after=False
    )

    return clicked_any


def check_phone_verification(driver):
    """
    Check if Instagram is asking for phone verification code.
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        tuple: (is_verification_required, verification_text)
    """
    try:
        page_source = driver.page_source.lower()
        current_url = driver.current_url.lower()
        
        # Check for phone verification indicators in page source
        verification_indicators = [
            "enter the code",
            "code sent to",
            "verification code",
            "confirm it's you",
            "confirm that it's you",
            "security code",
            "phone verification",
            "enter confirmation code",
            "we sent a code",
            "check your phone",
            "enter security code",
            "authentication code",
            "we'll send you a code",
            "suspicious activity",
            "unusual activity",
            "help us confirm it"
        ]
        
        # Check page source for verification text
        for indicator in verification_indicators:
            if indicator in page_source:
                if is_bot_debug_enabled():
                    print(f"-- DEBUG: Verification indicator found: '{indicator}'")
                return True, indicator
        
        # Check URL patterns for verification/challenge
        url_patterns = ["challenge", "accounts/confirm", "two_factor", "checkpoint"]
        for pattern in url_patterns:
            if pattern in current_url:
                if is_bot_debug_enabled():
                    print(f"-- DEBUG: Verification URL pattern found: '{pattern}'")
                return True, f"challenge_url_{pattern}"
        
        # Check for code input field (various selectors)
        try:
            code_input_selectors = [
                "input[type='text'][name*='code']",
                "input[type='text'][name*='Code']",
                "input[type='text'][aria-label*='code']",
                "input[type='text'][aria-label*='Code']",
                "input[placeholder*='code']",
                "input[placeholder*='Code']",
                "input[name='verificationCode']",
                "input[name='security_code']",
                "input[autocomplete='one-time-code']"
            ]
            
            for selector in code_input_selectors:
                try:
                    code_inputs = driver.find_elements(By.CSS_SELECTOR, selector)
                    if code_inputs and len(code_inputs) > 0:
                        # Verify the input is visible (not hidden)
                        for code_input in code_inputs:
                            if code_input.is_displayed():
                                if is_bot_debug_enabled():
                                    print(f"-- DEBUG: Verification code input found with selector: '{selector}'")
                                return True, "code_input_field"
                except:
                    continue
        except:
            pass
        
        # Check for specific verification-related button text
        try:
            verification_button_text = ["send code", "get code", "request code", "resend code"]
            for btn_text in verification_button_text:
                if btn_text in page_source:
                    if is_bot_debug_enabled():
                        print(f"-- DEBUG: Verification button text found: '{btn_text}'")
                    return True, f"button_{btn_text}"
        except:
            pass
        
        return False, None
    
    except Exception as e:
        # If we can't check, assume no verification needed
        if is_bot_debug_enabled():
            print(f"-- DEBUG: Error checking phone verification: {str(e)}")
        return False, None


def check_login(driver, account=None):
    _acct = account or "login"
    moduleErrorsLog = ""
    try:
        # Check if driver is still connected before attempting operations
        try:
            driver.current_url  # Quick check to see if driver is still connected
        except Exception:
            error_msg = "Driver connection lost - cannot check login status"
            moduleErrorsLog += error_msg
            return False, None, moduleErrorsLog
        
        # Same URL as do_login — avoids a second full page load when check then attempts credentials
        navigate_to_instagram_login_if_needed(driver, long_initial_settle=True)
        time.sleep(1.0)
        # One OS Escape burst + few Selenium rounds; repeated OS ESC was reloading IG and re-showing the sheet
        press_escape_to_dismiss_overlays(
            driver,
            presses=4,
            pause=0.45,
            context_label="check_login",
            os_esc_before=True,
            os_esc_after=False,
            os_presses=3,
        )
        dismiss_instagram_account_picker(driver, context_label="check_login")
        press_escape_to_dismiss_overlays(
            driver, presses=2, pause=0.35, context_label="check_login_light", os_esc_before=False
        )
        time.sleep(0.8)
        
        # Check for phone verification first
        is_verification_required, verification_reason = check_phone_verification(driver)
        if is_verification_required:
            error_msg = f"PHONE VERIFICATION REQUIRED - Reason: {verification_reason}"
            moduleErrorsLog += error_msg
            return "VERIFICATION_REQUIRED", None, moduleErrorsLog
        
        try:  # Method 1 — login form: wait for the username field
            press_escape_to_dismiss_overlays(
                driver, presses=1, pause=0.35, context_label="check_login_pre_username", os_esc_before=False
            )
            WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.NAME, "username")))
            login_fields = driver.find_elements(By.NAME, "username")
            if login_fields:
                print(client_log_line(_acct, "login", "check: login form detected"))
                return False, None, moduleErrorsLog
        except TimeoutException:
            pass  # Username field not found — possibly logged in
        
        try:  # Method 4 (moved up) — positive check: look for username in page source JSON
            page_source = driver.page_source
            
            # Search for the xdt_viewer.user.username pattern in JSON
            if '"xdt_viewer":{"user":{"username":"' in page_source:
                start = page_source.find('"xdt_viewer":{"user":{"username":"') + len(
                    '"xdt_viewer":{"user":{"username":"')
                end = page_source.find('"', start)
                username = page_source[start:end]
                if username:
                    return True, username, moduleErrorsLog
            
            # Fallback: search for viewerId username pattern
            if '"username":"' in page_source and '"id":"' in page_source:
                import re
                matches = re.findall(r'"username":"([^"]+)"', page_source)
                if matches:
                    for match in matches:
                        if len(match) > 3 and match.lower() not in ["sign up", "log in"]:
                            return True, match, moduleErrorsLog
        
        except:
            pass
        
        try:  # Method 3 (fallback) — login indicator text; only strings that don't appear on logged-in pages
            login_indicators = ["Trouble logging in?", "Forgot password?",
                                "Log in to Instagram", "Save login info"]
            WebDriverWait(driver, 12).until(
                lambda d: any(text.lower() in d.page_source.lower() for text in login_indicators)
            )
            print(client_log_line(_acct, "login", "check: login indicators detected"))
            return False, None, moduleErrorsLog
        except:
            pass
        
        return False, None, moduleErrorsLog
    
    except Exception as error:  ### catch all errors
        noteError = "check_login catch all"
        printError = True
        logError = True
        debugError = False
        moduleErrorsLog += process_exception(printError, noteError, logError, debugError)
        return False, None, moduleErrorsLog


def do_login(driver, username, password):
    """
    Attempt to log in to Instagram

    Args:
        driver: Selenium WebDriver instance
        username: Instagram username
        password: Instagram password

    Returns:
        tuple: (is_logged_in, current_user, errors)
    """
    moduleErrorsLog = ""
    
    try:
        # Check if driver is still connected before attempting operations
        try:
            driver.current_url  # Quick check to see if driver is still connected
        except Exception:
            error_msg = "Driver connection lost - cannot perform login"
            moduleErrorsLog += error_msg
            return False, None, moduleErrorsLog
        
        # Navigate only if not already on /accounts/login/ (check_login usually left us there)
        try:
            skipped_reload = navigate_to_instagram_login_if_needed(driver, long_initial_settle=True)
            # check_login already dismissed the account sheet; skip Escape here to avoid extra reloads
            if not skipped_reload:
                press_escape_to_dismiss_overlays(
                    driver,
                    presses=4,
                    pause=0.45,
                    context_label="do_login_post_nav",
                    os_esc_before=True,
                    os_esc_after=False,
                    os_presses=3,
                )
            dismiss_instagram_account_picker(driver, context_label="do_login")
            
            if is_bot_debug_enabled():
                print(f"-- DEBUG: Login page ready, current URL: {driver.current_url}")
            
        except Exception as error:
            noteError = f"Error navigating to login page: {str(error)}"
            printError = True
            logError = True
            debugError = False
            moduleErrorsLog += process_exception(printError, noteError, logError, debugError)
        
        # Enter username and password
        try:
            time.sleep(3.5)  # Wait for page to stabilize
            
            # OS Escape already ran after /accounts/login/ load; more PyAutoGUI ESC here tended to reload IG.
            press_escape_to_dismiss_overlays(
                driver, presses=3, pause=0.4, context_label="do_login_before_fields", os_esc_before=False
            )
            time.sleep(1.0)
            
            dismiss_instagram_account_picker(driver, context_label="do_login_pre_fields")
            
            # Check current URL after ESC to see if page changed
            try:
                current_url = driver.current_url
                if is_bot_debug_enabled():
                    print(f"-- DEBUG: Current URL after ESC: {current_url}")
            except Exception as e:
                print(client_log_line(None, "login", f"Could not get URL: {e}"))
            
            # Prefer name=username (avoids matching phone / other text fields)
            loginUsername = None
            username_selectors = [
                (By.CSS_SELECTOR, "input[name='username']"),
                (By.CSS_SELECTOR, "input[type='text'][autocomplete='username']"),
                (By.CSS_SELECTOR, "input[type='text']"),
                (By.XPATH, "//input[@type='text']"),
            ]
            
            for selector_type, selector_value in username_selectors:
                try:
                    loginUsername = WebDriverWait(driver, 18).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    break
                except Exception:
                    continue
            
            if not loginUsername:
                raise Exception("Could not find username input field")
            
            # Clear and enter username
            loginUsername.click()
            time.sleep(0.5)
            
            # Check for dialogs after clicking (clicking can trigger dialogs)
            if dismiss_browser_dialogs(driver, max_attempts=2):
                # Re-click the field after dismissing dialog
                loginUsername.click()
                time.sleep(0.5)
            
            loginUsername.clear()
            time.sleep(0.75)
            loginUsername.send_keys(username)
            time.sleep(0.75)
            
            if is_bot_debug_enabled():
                print(f"-- DEBUG: Username entered successfully")
            
            # Find password field
            loginPassword = None
            password_selectors = [
                (By.CSS_SELECTOR, "input[type='password']"),
                (By.CSS_SELECTOR, "input[name='password']"),
                (By.XPATH, "//input[@type='password']")
            ]
            
            for selector_type, selector_value in password_selectors:
                try:
                    loginPassword = WebDriverWait(driver, 18).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    break
                except Exception:
                    continue
            
            if not loginPassword:
                raise Exception("Could not find password input field")
            
            # Clear and enter password
            loginPassword.click()
            time.sleep(0.5)
            
            # Check for dialogs after clicking password field
            if dismiss_browser_dialogs(driver, max_attempts=2):
                # Re-click the field after dismissing dialog
                loginPassword.click()
                time.sleep(0.5)
            
            loginPassword.clear()
            time.sleep(0.75)
            loginPassword.send_keys(password)
            time.sleep(0.75)
            
            if is_bot_debug_enabled():
                print(f"-- DEBUG: Password entered successfully")
            
            login_submitted = submit_instagram_credentials(driver, loginPassword, log_name=username)
            if not login_submitted:
                if is_bot_debug_enabled():
                    print(f"-- DEBUG: [{username}] submit click failed, sending Return on password field")
                time.sleep(0.5)
                try:
                    loginPassword.send_keys(Keys.RETURN)
                except Exception:
                    pass
            
            # Wait for page to load after login attempt
            WebDriverWait(driver, 28).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            time.sleep(7)  # Give extra time for Instagram to process login
            
            # Immediately check for verification after submitting credentials
            if is_bot_debug_enabled():
                print(f"-- DEBUG: Checking for verification prompt after login submission...")
            is_verification, verify_reason = check_phone_verification(driver)
            if is_verification:
                if is_bot_debug_enabled():
                    print(f"-- DEBUG: Verification detected immediately after login: {verify_reason}")
                error_msg = f"PHONE VERIFICATION REQUIRED - Reason: {verify_reason}"
                moduleErrorsLog += error_msg
                return "VERIFICATION_REQUIRED", None, moduleErrorsLog
        
        except Exception as error:
            noteError = f"Error entering credentials: {str(error)}"
            printError = True
            logError = True
            debugError = False
            moduleErrorsLog += process_exception(printError, noteError, logError, debugError)
            
            # ALWAYS print error details for login failures (not just in debug mode)
            try:
                current_url = driver.current_url
                print(client_log_line(username, "login", f"error url: {current_url}"))
                print(client_log_line(username, "login", f"error {str(error)}"))
            except Exception as url_error:
                print(client_log_line(username, "login", f"error {str(error)} (couldn't get URL: {url_error})"))
            
            return False, None, moduleErrorsLog
        
        # Check results of login attempt
        try:
            # Wait for page to fully load
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            time.sleep(4.5)
            
            # Handle "Save login info" prompt if it appears after successful login
            try:
                page_source = driver.page_source.lower()
                if "save your login info" in page_source or "save login info" in page_source:
                    if is_bot_debug_enabled():
                        print(f"-- DEBUG: 'Save login info' prompt detected, looking for 'Not now' button...")
                    # Try to click "Not now" to skip saving login info
                    not_now_selectors = [
                        (By.XPATH, "//button[contains(text(), 'Not now') or contains(text(), 'Not Now')]"),
                        (By.XPATH, "//div[contains(text(), 'Not now') or contains(text(), 'Not Now')]//ancestor::button"),
                        (By.CSS_SELECTOR, "button._acan._acap._acas._aj1-")
                    ]
                    
                    for selector_type, selector_value in not_now_selectors:
                        try:
                            not_now_button = WebDriverWait(driver, 6).until(
                                EC.element_to_be_clickable((selector_type, selector_value))
                            )
                            not_now_button.click()
                            if is_bot_debug_enabled():
                                print(f"-- DEBUG: Clicked 'Not now' on save login info prompt")
                            time.sleep(2.5)
                            break
                        except Exception:
                            continue
            except Exception as e:
                if is_bot_debug_enabled():
                    print(f"-- DEBUG: Error handling 'Save login info' prompt: {str(e)}")
                pass  # Continue even if we can't dismiss this prompt
            
            # Handle notifications prompt if it appears
            try:
                page_source = driver.page_source.lower()
                if "turn on notifications" in page_source or "enable notifications" in page_source:
                    if is_bot_debug_enabled():
                        print(f"-- DEBUG: Notifications prompt detected, looking for 'Not now' button...")
                    not_now_selectors = [
                        (By.XPATH, "//button[contains(text(), 'Not Now') or contains(text(), 'Not now')]"),
                        (By.XPATH, "//div[contains(text(), 'Not Now') or contains(text(), 'Not now')]//ancestor::button")
                    ]
                    
                    for selector_type, selector_value in not_now_selectors:
                        try:
                            not_now_button = WebDriverWait(driver, 6).until(
                                EC.element_to_be_clickable((selector_type, selector_value))
                            )
                            not_now_button.click()
                            if is_bot_debug_enabled():
                                print(f"-- DEBUG: Clicked 'Not now' on notifications prompt")
                            time.sleep(2.5)
                            break
                        except Exception:
                            continue
            except Exception as e:
                if is_bot_debug_enabled():
                    print(f"-- DEBUG: Error handling notifications prompt: {str(e)}")
                pass  # Continue even if we can't dismiss this prompt
            
            # Check again for verification (in case it appeared after page load)
            is_verification_required, verification_reason = check_phone_verification(driver)
            if is_verification_required:
                error_msg = f"PHONE VERIFICATION REQUIRED - Reason: {verification_reason}"
                moduleErrorsLog += error_msg
                return "VERIFICATION_REQUIRED", None, moduleErrorsLog
            
            # Look for username in page source JSON data
            page_source = driver.page_source
            
            # Search for the xdt_viewer.user.username pattern in JSON
            if '"xdt_viewer":{"user":{"username":"' in page_source:
                start = page_source.find('"xdt_viewer":{"user":{"username":"') + len(
                    '"xdt_viewer":{"user":{"username":"')
                end = page_source.find('"', start)
                logged_in_user = page_source[start:end]
                if logged_in_user:
                    return True, logged_in_user, moduleErrorsLog
            
            # Fallback: check for other username patterns
            if '"username":"' in page_source:
                import re
                matches = re.findall(r'"username":"([^"]+)"', page_source)
                if matches:
                    # Filter out common non-username matches
                    for match in matches:
                        if len(match) > 3 and match.lower() not in ["sign up", "log in", "instagram"]:
                            return True, match, moduleErrorsLog
            
            # Check if we're still on login page (login failed)
            if any(text in page_source.lower() for text in ["log in to instagram", "trouble logging in", "forgot password"]):
                moduleErrorsLog += "Still on login page after login attempt - login likely failed"
                return False, None, moduleErrorsLog
                
        except Exception as error:
            noteError = f"Error verifying login: {str(error)}"
            printError = False
            logError = True
            debugError = False
            moduleErrorsLog += process_exception(printError, noteError, logError, debugError)
        
        return False, None, moduleErrorsLog
    
    except Exception as error:  ### catch all errors
        noteError = f"do_login catch all: {str(error)}"
        printError = True
        logError = True
        debugError = False
        moduleErrorsLog += process_exception(printError, noteError, logError, debugError)
        return False, None, moduleErrorsLog


def switch_login(driver, targetAccount):
    moduleErrorsLog = ""
    try:
        try:
            ## find and click the "More" button - handle both expanded and collapsed states
            try:
                # Try to find the Settings SVG and click its parent anchor tag
                moreButton = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, "//svg[@aria-label='Settings']/ancestor::a"))
                )
            except:
                # Try expanded state (text visible)
                moreButton = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'More')]/ancestor::a"))
                )
            
            moreButton.click()
            time.sleep(3)
            
            ## wait for and click the "Switch accounts" option in the menu
            switchLink = WebDriverWait(driver, 14).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Switch accounts')]"))
            )
            switchLink.click()
            
            time.sleep(random.randint(4, 7))
        except (NoSuchElementException, StaleElementReferenceException, TimeoutException) as e:
            moduleErrorsLog += f"cant find switch account link: {str(e)}"
            return False, None, moduleErrorsLog
        
        try:
            wait = WebDriverWait(driver, 14)
            
            # 1) Use the newest switcher container (menu/dialog/listbox)
            container_xp = "(//div[@role='menu' or @role='dialog' or @role='listbox'])[last()]"
            menu_container = wait.until(EC.visibility_of_element_located((By.XPATH, container_xp)))
            
            # 2) Find the exact account label INSIDE that container (prefer <span>, fall back to <div>)
            try:
                name_el = menu_container.find_element(By.XPATH, f".//span[normalize-space(text())='{targetAccount}']")
            except Exception:
                name_el = menu_container.find_element(By.XPATH, f".//div[normalize-space(text())='{targetAccount}']")
            
            # 3) Scroll the label into the dialog's view (no window scrolling)
            driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'nearest'});", name_el)
            
            # 4) Click the nearest clickable ancestor (anchors/buttons/role-rows)
            clickable = driver.execute_script("""
                const el = arguments[0];
                return el.closest('a,button,[role="menuitem"],[role="option"],[role="menuitemradio"],[role="button"]') || el;
            """, name_el)
            
            # Make sure that specific element is visible, then click
            wait.until(EC.visibility_of(clickable))
            try:
                clickable.click()
            except Exception:
                # Fallback: JS click avoids coordinate hit-tests
                driver.execute_script("arguments[0].click();", clickable)
            
            time.sleep(6.5)
        
        
        except (NoSuchElementException, StaleElementReferenceException, TimeoutException) as e:
            moduleErrorsLog += f"Target account '{targetAccount}' not found in switch list: {str(e)}"
            return False, None, moduleErrorsLog
        
        #### check results of switch attempt
        WebDriverWait(driver, 20).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(4.5)
        
        # Extract username from page source JSON data
        try:
            page_source = driver.page_source
            
            if '"xdt_viewer":{"user":{"username":"' in page_source:
                start = page_source.find('"xdt_viewer":{"user":{"username":"') + len(
                    '"xdt_viewer":{"user":{"username":"')
                end = page_source.find('"', start)
                current_ActiveAccount = page_source[start:end]
                
                if current_ActiveAccount and targetAccount.lower() == current_ActiveAccount.lower():
                    return True, current_ActiveAccount, moduleErrorsLog
        except:
            pass
        
        moduleErrorsLog += f"Switch verification failed. Expected: {targetAccount}"
        return False, None, moduleErrorsLog
    
    except Exception as error:  ### catch all errors
        noteError = "switch_login catch all"
        printError = True
        logError = True
        debugError = True
        moduleErrorsLog += process_exception(printError, noteError, logError, debugError)
        return False, None, moduleErrorsLog


def handle_account_login(driver, account, accountPass, apiClient=None):
    """
    Handle the complete login flow for an Instagram account.
    Includes login checking, login attempts, phone verification, and account switching.

    Args:
        driver: Selenium WebDriver instance
        account: Target Instagram account username
        accountPass: Account password
        apiClient: ApiClient instance for reading session settings

    Returns:
        tuple: (login_success, current_user, login_failure_exit, attempts_made, verification_requested)
        - login_success: True if successfully logged in to target account
        - current_user: Username of currently logged in user (or None)
        - login_failure_exit: True if login failed and should exit/skip bot script
        - attempts_made: Number of login attempts made
        - verification_requested: True if Instagram requested verification code
    """
    # Load login settings from API
    _user_cfg = apiClient.get_user_config() if apiClient else {}
    skipLoginCheck = _user_cfg.get('skip_login_check', False)
    login_tries = _user_cfg.get('login_tries', 3)
    
    loginFailureExit = False
    attempts_made = 0
    verification_requested = False
    
    if skipLoginCheck:
        print(client_log_line(account, "login", "skipping login check (manual setting)"))
        return True, account, False, 0, False  # Assume logged in if skipping check
    else:
        current_user = None
        is_logged_in = False
        
        for attempt in range(1, login_tries + 1):
            attempts_made = attempt
            # Check login status
            print(client_log_line(account, "login", f"check try={attempt}/{login_tries} → checking"))
            is_logged_in, current_user, loginErrors = check_login(driver, account=account)
            
            # Check if phone verification is required
            if is_logged_in == "VERIFICATION_REQUIRED":
                print(client_log_line(
                    account, "login",
                    f"verification challenge try={attempt}/{login_tries} (SMS or security code)",
                ))
                loginFailureExit = True
                verification_requested = True
                break
            
            # Log errors if any (to console only, session log will capture final result)
            if loginErrors and is_bot_debug_enabled():
                print(client_log_line(account, "login", f"debug check_login errors: {loginErrors}"))
            
            print(client_log_line(
                account, "login",
                f"check try={attempt}/{login_tries} → ok={is_logged_in} user={current_user}",
            ))
            
            # Attempt login if needed
            if not is_logged_in:
                print(client_log_line(account, "login", f"login try={attempt}/{login_tries} → attempting"))
                is_logged_in, current_user, loginErrors = do_login(driver, account, accountPass)
                
                if is_logged_in == "VERIFICATION_REQUIRED":
                    print(client_log_line(
                        account, "login",
                        f"verification challenge try={attempt}/{login_tries} (SMS or security code)",
                    ))
                    loginFailureExit = True
                    verification_requested = True
                    break
                
                # Log errors if any (to console only, session log will capture final result)
                if loginErrors and is_bot_debug_enabled():
                    print(client_log_line(account, "login", f"debug do_login errors: {loginErrors}"))
                
                print(client_log_line(
                    account, "login",
                    f"login try={attempt}/{login_tries} → ok={is_logged_in} user={current_user}",
                ))
            
            # Switch account if needed (skip if verification required)
            if is_logged_in and is_logged_in != "VERIFICATION_REQUIRED" and account != current_user:
                print(client_log_line(account, "login", f"switch try={attempt}/{login_tries} → switching"))
                is_logged_in, current_user, loginErrors = switch_login(driver, account)
                
                # Log errors if any (to console only, session log will capture final result)
                if loginErrors and is_bot_debug_enabled():
                    print(client_log_line(account, "login", f"debug switch_login errors: {loginErrors}"))
                
                print(client_log_line(
                    account, "login",
                    f"switch try={attempt}/{login_tries} → ok={is_logged_in} user={current_user}",
                ))
            
            # Break if successful (skip if verification required)
            if account == current_user and is_logged_in and is_logged_in != "VERIFICATION_REQUIRED":
                # Note: Success will be logged by accountSession.py in log_session_run()
                return True, current_user, False, attempts_made, False
            
            time.sleep(4 + attempt)
        
        # Exit if not logged in or in wrong account (or verification still required)
        if account != current_user or not is_logged_in or is_logged_in == "VERIFICATION_REQUIRED":
            loginFailureExit = True
            
            if is_logged_in == "VERIFICATION_REQUIRED":
                verification_requested = True
                # Challenge already summarized above; avoid repeating ERROR line
                return False, current_user, True, attempts_made, verification_requested
            
            error_msg = f"Login failure - wrong user: {current_user} or not logged in: {is_logged_in}"
            print(client_log_line(account, "login", f"failed — {error_msg}"))
            return False, current_user, True, attempts_made, verification_requested
        
        # Should not reach here, but return success if we do
        return True, current_user, False, attempts_made, False