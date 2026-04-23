# burnBot_unfollowDatabase.py

from burnBot_imports import *
from burnBot_utils import process_exception
from datetime import date, datetime, timedelta
import random
import time


def ensure_dialog_open(driver, dialog_type):
    """Ensure the correct dialog is open and ready for searching"""
    try:
        # Close any existing dialog first to ensure we open the right one
        try:
            close_button = driver.find_element(By.XPATH, "//div[@role='dialog']//button[contains(@aria-label, 'Close')]")
            close_button.click()
            time.sleep(0.5)
        except:
            pass

        # Open the requested dialog
        if 'following' in dialog_type.lower():
            link = driver.find_element(By.PARTIAL_LINK_TEXT, "following")
        else:
            link = driver.find_element(By.PARTIAL_LINK_TEXT, "followers")

        ActionChains(driver).move_to_element(link).click().perform()
        time.sleep(random.randint(2, 4))

        # Verify dialog opened
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
        )
        return True
    except Exception as e:
        return False


def search_for_profile(driver, username, target_username):
    """Helper function to check search box for profile"""
    try:
        # Wait for dialog to be present
        dialog = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
        )
        time.sleep(0.5)

        # Find search box - try multiple selectors
        searchBox = None
        try:
            searchBox = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='dialog']//input[@type='text']"))
            )
        except:
            try:
                searchBox = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, 'xhtitgo'))
                )
            except:
                pass

        if not searchBox:
            return False, None

        # Click to focus
        ActionChains(driver).move_to_element(searchBox).click().perform()
        time.sleep(0.5)

        # Clear any existing text
        searchBox.clear()
        time.sleep(0.5)

        # Type text
        search_text = username[:20]
        searchBox.send_keys(search_text)
        time.sleep(0.5)

        # Verify text was entered - if not, use JavaScript
        current_value = searchBox.get_attribute('value')
        if not current_value or len(current_value) == 0:
            driver.execute_script("arguments[0].value = arguments[1];", searchBox, search_text)
            driver.execute_script("""
                var event = new Event('input', { bubbles: true });
                arguments[0].dispatchEvent(event);
            """, searchBox)
            time.sleep(0.5)

        time.sleep(1)

        # Wait for results to load
        profile_link = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((
                By.XPATH,
                f"//div[@role='dialog']//a[@href='/{target_username}/']"
            ))
        )
        return True, profile_link

    except (NoSuchElementException, TimeoutException):
        return False, None
    except Exception:
        return False, None


def do_unfollow_database(driver, account, target_count, apiClient, account_id, unfollow_days=30):
    """
    Unfollow accounts from follow targets database via API

    Args:
        driver: Selenium WebDriver instance
        account: Account name (for logging)
        target_count: Maximum number of accounts to unfollow
        apiClient: ApiClient instance for API access
        account_id: Account UUID
        unfollow_days: Number of days to wait before unfollowing (default: 30)

    Returns:
        tuple: (unfollows_performed, errors_log)
    """
    unfollows_performed = 0
    moduleErrorsLog = ""

    try:
        today = date.today()
        unfollow_date = today

        print(f"- [{account}]: [unfollow][database] - loading account data...")

        # Get eligible follow targets from API (status=following, older than unfollow_days)
        try:
            targets = apiClient.get_follow_targets(
                account_id, status="following", older_than_days=unfollow_days,
                page_size=target_count
            )
        except Exception as e:
            print(f"- [{account}]: [unfollow][database] - ERROR: Could not load follow targets: {e}")
            return 0, f"Could not load follow targets: {e}"

        if not targets:
            print(f"- [{account}]: [unfollow][database] - no eligible accounts found (all too recent, done, or private)")
            return 0, ""

        print(f"- [{account}]: [unfollow][database] - found {len(targets)} eligible account(s)")

        # Navigate to account profile
        print(f"- [{account}]: [unfollow][database] - loading profile page...")
        active_account_page = f"https://www.instagram.com/{account}/"
        driver.get(active_account_page)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(random.randint(2, 4))

        # Save the main window handle
        main_window = driver.current_window_handle

        # Open following in new tab
        print(f"- [{account}]: [unfollow][database] - opening following tab...")
        driver.switch_to.new_window('tab')
        driver.get(active_account_page)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(random.randint(2, 4))

        following_window = driver.current_window_handle

        # Click following link to open dialog
        try:
            following_link = driver.find_element(By.PARTIAL_LINK_TEXT, "following")
            ActionChains(driver).move_to_element(following_link).click().perform()
            time.sleep(random.randint(2, 4))
        except Exception as e:
            print(f"- [{account}]: [unfollow][database] - ERROR: Could not open following dialog")
            driver.close()
            driver.switch_to.window(main_window)
            return 0, f"Could not open following dialog: {e}"

        # Open followers in new tab
        print(f"- [{account}]: [unfollow][database] - opening followers tab...")
        driver.switch_to.new_window('tab')
        driver.get(active_account_page)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(random.randint(2, 4))

        followers_window = driver.current_window_handle

        # Click followers link to open dialog
        try:
            followers_link = driver.find_element(By.PARTIAL_LINK_TEXT, "followers")
            ActionChains(driver).move_to_element(followers_link).click().perform()
            time.sleep(random.randint(2, 4))
        except Exception as e:
            print(f"- [{account}]: [unfollow][database] - ERROR: Could not open followers dialog")
            driver.close()
            driver.switch_to.window(following_window)
            driver.close()
            driver.switch_to.window(main_window)
            return 0, f"Could not open followers dialog: {e}"

        # Process each target
        target_formatted = f"{target_count:02d}"

        for target in targets:
            if unfollows_performed >= target_count:
                break

            loop_username = target.get("target_handle", "")
            target_id = target.get("id", "")

            if not loop_username:
                continue

            unfollows_performed += 1
            count_formatted = f"{unfollows_performed:02d}"

            print(f"- [{account}]: [unfollow][database] - [{count_formatted}/{target_formatted}] - [{loop_username}]", end="")

            # Create username variations to try (reversed order)
            loop_username_clean = loop_username.replace(".", "").replace("_", "")
            loop_username_short = loop_username[:20]
            loop_username_clean_short = loop_username_clean[:20]

            usernames_to_try = []
            for username in [loop_username_clean_short, loop_username_short, loop_username_clean, loop_username]:
                if username not in usernames_to_try:
                    usernames_to_try.append(username)

            # Check if they follow back (check followers tab first)
            follow_back = False

            # Switch to followers tab
            driver.switch_to.window(followers_window)
            time.sleep(1)

            # Search in followers list
            found_in_followers = False
            for username in usernames_to_try:
                found_in_followers, _ = search_for_profile(driver, username, loop_username)
                if found_in_followers:
                    break
                time.sleep(0.3)

            if found_in_followers:
                follow_back = True

            follow_back_display = "yes" if follow_back else "no"

            # Switch to following tab for unfollowing
            driver.switch_to.window(following_window)
            time.sleep(1)

            # Search for profile in following list
            found = False
            profile_link = None
            for username in usernames_to_try:
                found, profile_link = search_for_profile(driver, username, loop_username)
                if found:
                    break
                time.sleep(0.3)

            if found and profile_link:
                try:
                    # Find the account box and unfollow button
                    account_box = profile_link.find_element(By.XPATH,
                                                           "ancestor::div[contains(@class, 'x1uhb9sk') or contains(@class, 'x1n2onr6')]")
                    follow_button = account_box.find_element(By.XPATH, ".//button[.//div[contains(text(), 'ollow')]]")

                    # Click to trigger unfollow modal
                    ActionChains(driver).move_to_element(follow_button).click().perform()
                    time.sleep(random.randint(3, 5))

                    # Click unfollow confirmation
                    unfollow_confirm = WebDriverWait(driver, 6).until(
                        EC.element_to_be_clickable((By.CLASS_NAME, "_a9-_"))
                    )
                    ActionChains(driver).move_to_element(unfollow_confirm).click().perform()

                    print(f" - [{follow_back_display}] - [done]")

                    # Update follow target via API
                    try:
                        apiClient.update_follow_target(
                            target_id,
                            status="done",
                            unfollow_date=unfollow_date,
                            follow_back=follow_back
                        )
                    except Exception as update_error:
                        moduleErrorsLog += f"Could not update target for {loop_username}: {update_error}\n"

                    time.sleep(random.randint(4, 6))

                except Exception as e:
                    print(f" - [ error ]")
                    moduleErrorsLog += f"Error unfollowing {loop_username}: {e}\n"
            else:
                # Account not found in following list (already unfollowed manually or by another process)
                # Still mark as done in database to avoid checking again
                print(f" - [{follow_back_display}] - [skip]")

                # Update follow target via API
                try:
                    apiClient.update_follow_target(
                        target_id,
                        status="done",
                        unfollow_date=unfollow_date,
                        follow_back=follow_back
                    )
                except Exception as update_error:
                    moduleErrorsLog += f"Could not update target for {loop_username}: {update_error}\n"

                moduleErrorsLog += f"Not found in following list (already unfollowed): {loop_username}\n"

        # Summary message
        if unfollows_performed < target_count:
            print(f"- [{account}]: [unfollow][database] - completed {unfollows_performed} (no more eligible accounts)")
        else:
            print(f"- [{account}]: [unfollow][database] - target reached ({unfollows_performed}/{target_count})")

        # Close extra tabs and return to main window
        driver.switch_to.window(followers_window)
        driver.close()
        driver.switch_to.window(following_window)
        driver.close()
        driver.switch_to.window(main_window)

    except Exception as error:
        noteError = "do_unfollow_database catch all"
        printError = True
        logError = True
        debugError = False
        moduleErrorsLog += process_exception(printError, noteError, logError, debugError)

    return unfollows_performed, moduleErrorsLog
