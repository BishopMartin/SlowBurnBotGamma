import time
import random
import builtins as _builtins
from datetime import date
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from burnBot_utils import process_exception
from burnBot_client_log import client_log_line
import burnBot_status as status_store

_p = _builtins.print  # set per-call by do_follow_group; safe because sessions run sequentially


def do_follow_group(driver, account, target_count, apiClient, account_id, group_type, target_accounts, _print=None, log_scope=None, action_label=None):
    global _p
    _p = _print if _print is not None else _builtins.print
    _scope = log_scope or "follow-group"
    _lbl = f"{action_label}-" if action_label else ""
    _done_lbl = (action_label[0].upper() + action_label[1:]) if action_label else "Done"
    """
    Follow accounts from a target account's followers or following list

    Args:
        driver: Selenium WebDriver instance
        account: Account username (self account)
        target_count: Number of accounts to follow
        apiClient: ApiClient instance for API access
        account_id: Account UUID
        group_type: "followers[group]" or "following[group]"
        target_accounts: Comma-separated list of target account usernames

    Returns:
        tuple: (followed_count, error_log_string)
    """
    module_errors_log = ""
    followed_count = 0

    try:
        today = date.today()
        follow_date = today

        # Load database of previously followed accounts from API
        try:
            database_names = list(apiClient.get_all_follow_target_handles(account_id))
        except Exception as e:
            _p(client_log_line(account, _scope, f"{_lbl}Warning: Could not load follow targets: {e}"))
            database_names = []

        # Add universal ignore list
        try:
            ignore_list = apiClient.get_ignore_handles()
            database_names.extend(ignore_list)
        except Exception as e:
            _p(client_log_line(account, _scope, f"{_lbl}Warning: Could not load ignore list: {e}"))

        _p(client_log_line(account, _scope, f"{_lbl}loaded {len(database_names)} existing entries"))
        
        # Parse target accounts and randomly select one
        target_accounts_list = [t.strip() for t in target_accounts.split(',') if t.strip()]
        if not target_accounts_list:
            _p(client_log_line(account, _scope, f"{_lbl}ERROR: No target accounts provided"))
            return 0, "No target accounts provided"
        
        target_account = random.choice(target_accounts_list)
        _p(client_log_line(account, _scope, f"{_lbl}selected target: {target_account}"))
        
        # Navigate to target account page
        target_account_page = f"https://www.instagram.com/{target_account}/"
        driver.get(target_account_page)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        time.sleep(random.uniform(3, 5))
        
        # Check if target account exists
        if driver.find_elements(By.XPATH, "//*[contains(text(), \"Sorry, this page isn't available.\")]"):
            error_msg = f"Target account '{target_account}' not found"
            _p(client_log_line(account, _scope, f"{_lbl}ERROR: {error_msg}"))
            return 0, error_msg
        
        # Determine which link to click (followers or following)
        if group_type in ("followers[group]", "account list [followers]"):
            link_text = 'followers'
            action_type = "followers"
        elif group_type in ("following[group]", "account list [following]"):
            link_text = 'following'
            action_type = "following"
        else:
            _p(client_log_line(account, _scope, f"{_lbl}ERROR: Invalid group type"))
            return 0, f"Invalid group type: {group_type}"
        
        # Find and click the followers/following link — try multiple strategies since
        # Instagram changes whether these are <a href=…>, <button>, or role="link" elements.
        _strategies = [
            # Instagram now uses <a href="#" role="link"> where text is split across child spans
            # and a text node " following"/" followers" — match by role + contains on full text.
            ("role-link-text",  By.XPATH, f"//a[@role='link'][contains(., ' {link_text}')]"),
            ("href-slash",      By.XPATH, f"//a[contains(@href, '/{link_text}/')]"),
            ("href-noslash",    By.XPATH, f"//a[contains(@href, '/{link_text}')]"),
            ("button-text",     By.XPATH, f"//button[.//*[normalize-space()='{link_text}']]"),
            ("role-link-exact", By.XPATH, f"//*[@role='link'][.//*[normalize-space()='{link_text}']]"),
            ("header-text",     By.XPATH, f"//header//*[normalize-space()='{link_text}']"),
        ]
        target_link = None
        matched_strategy = None
        for _strat_name, _by, _sel in _strategies:
            try:
                target_link = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((_by, _sel))
                )
                matched_strategy = _strat_name
                break
            except Exception:
                continue

        if target_link is None:
            error_msg = f"Failed to open {link_text} dialog: element not found with any selector strategy"
            _p(client_log_line(account, _scope, f"{_lbl}ERROR: {error_msg}"))
            return 0, error_msg

        _p(client_log_line(account, _scope, f"{_lbl}located {link_text} via [{matched_strategy}]"))
        try:
            actions = ActionChains(driver)
            actions.move_to_element(target_link)
            actions.perform()
            time.sleep(random.uniform(2, 4))

            actions = ActionChains(driver)
            actions.click(target_link)
            actions.perform()
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            error_msg = f"Failed to open {link_text} dialog: {e}"
            _p(client_log_line(account, _scope, f"{_lbl}ERROR: {error_msg}"))
            return 0, error_msg
        
        _p(client_log_line(account, _scope, f"{_lbl}dialog opened for {target_account}"))
        
        # Main follow loop
        user_boxes_done = []
        stall_scrolls = 0
        max_stall_scrolls = 5  # consecutive no-new-boxes scrolls before treating as end of list

        while followed_count < target_count:
            if status_store.is_bot_paused():
                return followed_count, module_errors_log
            try:
                # Find all user boxes in the dialog
                user_boxes_found = driver.find_elements(By.CLASS_NAME, "xozqiw3")
                user_boxes_new = [item for item in user_boxes_found if item not in user_boxes_done]

                if not user_boxes_new:
                    stall_scrolls += 1
                    if stall_scrolls >= max_stall_scrolls:
                        _p(client_log_line(account, _scope, f"{_lbl}Warning: reached end of list [{followed_count}/{target_count}]"))
                        break
                    # No new boxes, try scrolling
                    try:
                        window = driver.find_element(By.CLASS_NAME, 'xz65tgg')
                        window.send_keys(Keys.PAGE_DOWN)
                        time.sleep(random.uniform(2, 4))
                        continue
                    except Exception:
                        # Can't scroll anymore, we've reached the end
                        _p(client_log_line(account, _scope, f"{_lbl}Warning: reached end of list [{followed_count}/{target_count}]"))
                        break
                else:
                    stall_scrolls = 0

            except Exception as e:
                # Error loading user boxes, try scrolling
                try:
                    window = driver.find_element(By.CLASS_NAME, 'xz65tgg')
                    window.send_keys(Keys.PAGE_DOWN)
                    time.sleep(random.uniform(1, 3))
                    continue
                except Exception:
                    break
            
            # Process each new user box
            for user_box in user_boxes_new:
                if status_store.is_bot_paused() or followed_count >= target_count:
                    break
                
                try:
                    user_name_element = user_box.find_element(By.CLASS_NAME, "_aad7")
                    user_status_element = user_box.find_element(By.CLASS_NAME, "_aad6")
                    user_name = user_name_element.text
                    user_status = user_status_element.text
                except Exception:
                    # Skip if we can't get username/status
                    continue
                
                try:
                    # Check if already in database
                    if user_name in database_names:
                        _p(client_log_line(account, _scope, f"{target_account}[{action_type}]-[-skip] - [{user_name}] - [already followed]"))
                        time.sleep(random.uniform(1, 1))
                        continue
                    
                    # Check if already following
                    if user_status != "Follow":
                        _p(client_log_line(account, _scope, f"{target_account}[{action_type}]-[-skip] - [{user_name}] - [{user_status.lower()}]"))
                        time.sleep(random.uniform(1, 1))
                        continue
                    
                    # Hover over username to trigger profile preview
                    actions = ActionChains(driver)
                    actions.move_to_element(user_name_element)
                    actions.perform()
                    time.sleep(random.uniform(1, 1))
                    
                    # Check for stale element
                    if not user_name_element.text:
                        continue
                    
                    # Check if account is private
                    _is_private = 'The account is private' in driver.page_source
                    _skip_private = False
                    if _is_private:
                        user_config = apiClient.get_user_config() if apiClient else None
                        _skip_private = bool(user_config and user_config.get('skip_private', False))
                    if _is_private and _skip_private:
                        # Log private account via API
                        target_source = f"{target_account}[{action_type}]"
                        try:
                            apiClient.create_follow_target(
                                account_id, user_name, source=target_source,
                                status="private", follow_date=follow_date
                            )
                        except Exception:
                            pass

                        # Move hover away
                        actions = ActionChains(driver)
                        actions.move_to_element(target_link)
                        actions.perform()

                        _p(client_log_line(account, _scope, f"{target_account}[{action_type}]-[-skip] - [{user_name}] - [private]"))

                    else:
                        # Follow the account
                        followed_count += 1

                        actions = ActionChains(driver)
                        actions.move_to_element(user_status_element)
                        actions.click(user_status_element)
                        actions.perform()

                        # Log followed account via API
                        target_source = f"{target_account}[{action_type}]"
                        try:
                            apiClient.create_follow_target(
                                account_id, user_name, source=target_source,
                                status="following", follow_date=follow_date
                            )
                        except Exception:
                            pass

                        _p(client_log_line(account, _scope, f"{target_account}[{action_type}]-[{followed_count:02d}/{target_count:02d}] - [{user_name}]"))
                        
                        # Delay between follows
                        time.sleep(random.uniform(10, 20))
                
                except StaleElementReferenceException:
                    continue
                
                except Exception as e:
                    error_msg = process_exception(True, f"follow user failed: {e}", True, False)
                    module_errors_log += error_msg
                    continue
            
            # Mark these boxes as done
            user_boxes_done.extend(user_boxes_found)
            
            # Scroll down to load more users
            if followed_count < target_count:
                try:
                    window = driver.find_element(By.CLASS_NAME, 'xz65tgg')
                    window.send_keys(Keys.PAGE_DOWN)
                    time.sleep(random.uniform(2, 4))
                    
                    # Scroll again for good measure
                    window = driver.find_element(By.CLASS_NAME, 'xz65tgg')
                    window.send_keys(Keys.PAGE_DOWN)
                    time.sleep(random.uniform(2, 4))
                
                except StaleElementReferenceException:
                    try:
                        window = driver.find_element(By.CLASS_NAME, 'xz65tgg')
                        window.send_keys(Keys.PAGE_DOWN)
                        time.sleep(random.uniform(2, 4))
                    except Exception:
                        pass
                except Exception:
                    pass
        
        _p(client_log_line(account, _scope, f"{_done_lbl}-Completed[{followed_count}/{target_count}]"))
    
    except Exception as e:
        error_msg = process_exception(True, f"follow group failed: {e}", True, True)
        module_errors_log += error_msg
    
    return followed_count, module_errors_log


