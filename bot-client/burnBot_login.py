# burnBot_login.py

from burnBot_imports import *
from burnBot_utils import close_windows, has_internet_connection, process_exception, delay


def is_bot_debug_enabled():
    """Check if bot_debug is enabled in config"""
    try:
        from burnBot_config import CONFIG
        return CONFIG.getboolean('bot_settings', 'bot_debug', fallback=False)
    except Exception:
        return False


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
            print(f"- [LOGIN]: Browser dialog #{dialogs_dismissed + 1} detected: '{alert_text}' - dismissing...")
            alert.accept()  # Try accepting instead of dismissing
            dialogs_dismissed += 1
            time.sleep(wait_between)
        except Exception:
            # No alert present
            if dialogs_dismissed > 0:
                time.sleep(0.2)  # Brief pause to ensure dialog is fully gone
            break
    
    if dialogs_dismissed > 0:
        print(f"- [LOGIN]: Dismissed {dialogs_dismissed} browser dialog(s)")
    
    return dialogs_dismissed


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
        
        driver.get("https://www.instagram.com/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)
        
        # Check for phone verification first
        is_verification_required, verification_reason = check_phone_verification(driver)
        if is_verification_required:
            error_msg = f"PHONE VERIFICATION REQUIRED - Reason: {verification_reason}"
            moduleErrorsLog += error_msg
            return "VERIFICATION_REQUIRED", None, moduleErrorsLog
        
        try:  # Method 1 — login form: wait up to 5 seconds for the username field
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, "username")))
            login_fields = driver.find_elements(By.NAME, "username")
            if login_fields:
                print(f"- [{_acct}]: [login][check] login form detected")
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
            WebDriverWait(driver, 5).until(
                lambda d: any(text.lower() in d.page_source.lower() for text in login_indicators)
            )
            print(f"- [{_acct}]: [login][check] login indicators detected")
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
        
        # Navigate to Instagram login page if not already there
        try:
            driver.get("https://www.instagram.com/accounts/login/")
            
            # Wait for page body to load
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Wait for page to be fully loaded
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # Extra wait for dynamic content to render
            time.sleep(4)
            
            if is_bot_debug_enabled():
                print(f"-- DEBUG: Login page loaded, current URL: {driver.current_url}")
            
        except Exception as error:
            noteError = f"Error navigating to login page: {str(error)}"
            printError = True
            logError = True
            debugError = False
            moduleErrorsLog += process_exception(printError, noteError, logError, debugError)
        
        # Enter username and password
        try:
            time.sleep(2)  # Wait for page to stabilize
            
            # Dismiss any Chrome dialogs with ESC before entering credentials
            # Must be done BEFORE any clicks since the dialog blocks interaction
            try:
                try:
                    import pyautogui
                    import pygetwindow as gw
                    
                    # Find Chrome window by title and activate it
                    try:
                        chrome_windows = gw.getWindowsWithTitle('Instagram')
                        if not chrome_windows:
                            chrome_windows = gw.getWindowsWithTitle('Chrome')
                        
                        if chrome_windows:
                            chrome_window = chrome_windows[0]
                            chrome_window.activate()
                            time.sleep(0.5)
                            if is_bot_debug_enabled():
                                print(f"-- DEBUG: Chrome window activated: {chrome_window.title}")
                        else:
                            if is_bot_debug_enabled():
                                print(f"-- DEBUG: Could not find Chrome window")
                    except Exception as e:
                        if is_bot_debug_enabled():
                            print(f"-- DEBUG: Could not activate window: {e}")
                    
                    # Press ESC to dismiss the dialog
                    if is_bot_debug_enabled():
                        print(f"-- DEBUG: Pressing ESC to dismiss dialog...")
                    for i in range(5):
                        pyautogui.press('esc')
                        time.sleep(0.4)
                    if is_bot_debug_enabled():
                        print(f"-- DEBUG: ESC pressed 5 times")
                    
                except ImportError as e:
                    if is_bot_debug_enabled():
                        print(f"-- DEBUG: Required library not installed: {e}")
                
                time.sleep(1)
            except Exception as e:
                if is_bot_debug_enabled():
                    print(f"-- DEBUG: Error dismissing dialog: {e}")
            
            # Check current URL after ESC to see if page changed
            try:
                current_url = driver.current_url
                if is_bot_debug_enabled():
                    print(f"-- DEBUG: Current URL after ESC: {current_url}")
            except Exception as e:
                print(f"- [LOGIN]: Could not get URL: {e}")
            
            # Find username field (input[type='text'] is most reliable)
            loginUsername = None
            username_selectors = [
                (By.CSS_SELECTOR, "input[type='text']"),
                (By.CSS_SELECTOR, "input[name='username']"),
                (By.XPATH, "//input[@type='text']")
            ]
            
            for selector_type, selector_value in username_selectors:
                try:
                    loginUsername = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    break
                except Exception:
                    continue
            
            if not loginUsername:
                raise Exception("Could not find username input field")
            
            # Clear and enter username
            loginUsername.click()
            time.sleep(0.3)
            
            # Check for dialogs after clicking (clicking can trigger dialogs)
            if dismiss_browser_dialogs(driver, max_attempts=2):
                # Re-click the field after dismissing dialog
                loginUsername.click()
                time.sleep(0.3)
            
            loginUsername.clear()
            time.sleep(0.5)
            loginUsername.send_keys(username)
            time.sleep(0.5)
            
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
                    loginPassword = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    break
                except Exception:
                    continue
            
            if not loginPassword:
                raise Exception("Could not find password input field")
            
            # Clear and enter password
            loginPassword.click()
            time.sleep(0.3)
            
            # Check for dialogs after clicking password field
            if dismiss_browser_dialogs(driver, max_attempts=2):
                # Re-click the field after dismissing dialog
                loginPassword.click()
                time.sleep(0.3)
            
            loginPassword.clear()
            time.sleep(0.5)
            loginPassword.send_keys(password)
            time.sleep(0.5)
            
            if is_bot_debug_enabled():
                print(f"-- DEBUG: Password entered successfully")
            
            # Try to find and click the login button
            login_submitted = False
            try:
                login_button_selectors = [
                    (By.CSS_SELECTOR, "button[type='submit']"),
                    (By.XPATH, "//button[@type='submit']"),
                    (By.XPATH, "//button[contains(text(), 'Log in') or contains(text(), 'Log In')]")
                ]
                
                for selector_type, selector_value in login_button_selectors:
                    try:
                        loginButton = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((selector_type, selector_value))
                        )
                        time.sleep(0.5)
                        loginButton.click()
                        login_submitted = True
                        break
                    except Exception:
                        continue
            except Exception:
                pass  # Will use Enter key fallback
            
            # Fallback to pressing Enter if button click failed
            if not login_submitted:
                time.sleep(0.5)
                loginPassword.send_keys(Keys.RETURN)
            
            # Wait for page to load after login attempt
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            time.sleep(5)  # Give extra time for Instagram to process login
            
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
                print(f"- [{username}]: [login][error] url: {current_url}")
                print(f"- [{username}]: [login][error] {str(error)}")
            except Exception as url_error:
                print(f"- [{username}]: [login][error] {str(error)} (couldn't get URL: {url_error})")
            
            return False, None, moduleErrorsLog
        
        # Check results of login attempt
        try:
            # Wait for page to fully load
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            time.sleep(3)
            
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
                            not_now_button = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((selector_type, selector_value))
                            )
                            not_now_button.click()
                            if is_bot_debug_enabled():
                                print(f"-- DEBUG: Clicked 'Not now' on save login info prompt")
                            time.sleep(2)
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
                            not_now_button = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((selector_type, selector_value))
                            )
                            not_now_button.click()
                            if is_bot_debug_enabled():
                                print(f"-- DEBUG: Clicked 'Not now' on notifications prompt")
                            time.sleep(2)
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
                moreButton = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//svg[@aria-label='Settings']/ancestor::a"))
                )
            except:
                # Try expanded state (text visible)
                moreButton = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'More')]/ancestor::a"))
                )
            
            moreButton.click()
            time.sleep(2)
            
            ## wait for and click the "Switch accounts" option in the menu
            switchLink = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Switch accounts')]"))
            )
            switchLink.click()
            
            time.sleep(random.randint(3, 5))
        except (NoSuchElementException, StaleElementReferenceException, TimeoutException) as e:
            moduleErrorsLog += f"cant find switch account link: {str(e)}"
            return False, None, moduleErrorsLog
        
        try:
            wait = WebDriverWait(driver, 10)
            
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
            
            time.sleep(5)
        
        
        except (NoSuchElementException, StaleElementReferenceException, TimeoutException) as e:
            moduleErrorsLog += f"Target account '{targetAccount}' not found in switch list: {str(e)}"
            return False, None, moduleErrorsLog
        
        #### check results of switch attempt
        WebDriverWait(driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(3)
        
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
        print(f"- [{account}]: skiping login check manual setting")
        return True, account, False, 0, False  # Assume logged in if skipping check
    else:
        current_user = None
        is_logged_in = False
        
        for attempt in range(1, login_tries + 1):
            attempts_made = attempt
            # Check login status
            print(f"- [{account}]: [login][check] status:[checking] try:[{attempt}/{login_tries}]")
            is_logged_in, current_user, loginErrors = check_login(driver, account=account)
            
            # Check if phone verification is required
            if is_logged_in == "VERIFICATION_REQUIRED":
                print(f"- [{account}]: [login][VERIFICATION] PHONE VERIFICATION CODE REQUESTED")
                print(f"- [{account}]: [login][VERIFICATION] Instagram is requesting verification code via SMS")
                # Note: Error will be logged by accountSession.py in log_session_run()
                
                # Stop additional login attempts immediately
                loginFailureExit = True
                verification_requested = True
                break
            
            # Log errors if any (to console only, session log will capture final result)
            if loginErrors and is_bot_debug_enabled():
                print(f"- [{account}]: [login][debug] check_login errors: {loginErrors}")
            
            print(f"- [{account}]: [login][check] status:[{is_logged_in}] user:[{current_user}] try:[{attempt}/{login_tries}]")
            
            # Attempt login if needed
            if not is_logged_in:
                print(f"- [{account}]: [login][login] status:[attempting] try:[{attempt}/{login_tries}]")
                is_logged_in, current_user, loginErrors = do_login(driver, account, accountPass)
                
                # Check if phone verification is required
                if is_logged_in == "VERIFICATION_REQUIRED":
                    print(f"- [{account}]: [login][VERIFICATION] PHONE VERIFICATION CODE REQUESTED")
                    print(f"- [{account}]: [login][VERIFICATION] Instagram is requesting verification code via SMS")
                    # Note: Error will be logged by accountSession.py in log_session_run()
                    
                    # Stop additional login attempts immediately
                    loginFailureExit = True
                    verification_requested = True
                    break
                
                # Log errors if any (to console only, session log will capture final result)
                if loginErrors and is_bot_debug_enabled():
                    print(f"- [{account}]: [login][debug] do_login errors: {loginErrors}")
                
                print(f"- [{account}]: [login][login] status:[{is_logged_in}] user:[{current_user}] try:[{attempt}/{login_tries}]")
            
            # Switch account if needed (skip if verification required)
            if is_logged_in and is_logged_in != "VERIFICATION_REQUIRED" and account != current_user:
                print(f"- [{account}]: [login][switch] status:[switching] try:[{attempt}/{login_tries}]")
                is_logged_in, current_user, loginErrors = switch_login(driver, account)
                
                # Log errors if any (to console only, session log will capture final result)
                if loginErrors and is_bot_debug_enabled():
                    print(f"- [{account}]: [login][debug] switch_login errors: {loginErrors}")
                
                print(f"- [{account}]: [login][switch] status:[{is_logged_in}] user:[{current_user}] try:[{attempt}/{login_tries}]")
            
            # Break if successful (skip if verification required)
            if account == current_user and is_logged_in and is_logged_in != "VERIFICATION_REQUIRED":
                # Note: Success will be logged by accountSession.py in log_session_run()
                return True, current_user, False, attempts_made, False
            
            time.sleep(3 + attempt)
        
        # Exit if not logged in or in wrong account (or verification still required)
        if account != current_user or not is_logged_in or is_logged_in == "VERIFICATION_REQUIRED":
            loginFailureExit = True
            
            # Provide specific error message for verification vs regular login failure
            if is_logged_in == "VERIFICATION_REQUIRED":
                verification_requested = True
                error_msg = "VERIFICATION_CODE_REQUESTED"
            else:
                error_msg = f"Login failure - wrong user: {current_user} or not logged in: {is_logged_in}"
            
            print(f"- [{account}]: ERROR - {error_msg}")
            # Note: Error will be logged by accountSession.py in log_session_run()
            return False, current_user, True, attempts_made, verification_requested
        
        # Should not reach here, but return success if we do
        return True, current_user, False, attempts_made, False