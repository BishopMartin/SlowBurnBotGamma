import time
import random
from datetime import date
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

def _extract_username_from_profile_href(href: str) -> str | None:
    """
    Extract an Instagram username from a profile URL.

    Accepts absolute or relative hrefs like:
    - https://www.instagram.com/someuser/
    - /someuser/

    Returns username or None if not a profile link.
    """
    if not href:
        return None

    try:
        # Normalize relative href to a parseable URL
        if href.startswith("/"):
            href = f"https://www.instagram.com{href}"

        path = urlparse(href).path or ""
        # Expected profile path: "/<username>/"
        parts = [p for p in path.split("/") if p]
        if len(parts) != 1:
            return None

        username = parts[0].strip()
        if not username:
            return None

        # Exclude non-profile routes
        reserved = {
            "accounts", "explore", "reels", "direct", "p", "tv", "stories",
            "about", "developer", "legal", "privacy", "terms",
        }
        if username.lower() in reserved:
            return None

        return username
    except Exception:
        return None


def _find_home_follow_candidates(driver, max_candidates: int = 50):
    """
    Find follow candidates on Instagram home page by locating Follow buttons and
    extracting the associated username from nearby profile links.

    Returns: list[tuple[str, WebElement, WebElement|None]]
      - (username, follow_button_element, username_anchor_element_or_None)
    """
    # Instagram UI varies: buttons can be <button> or <div role="button">
    follow_buttons = driver.find_elements(
        By.XPATH,
        (
            "//button[normalize-space()='Follow' or normalize-space()='Follow back']"
            " | //*[@role='button'][normalize-space()='Follow' or normalize-space()='Follow back']"
        ),
    )

    candidates = []
    seen = set()

    for btn in follow_buttons:
        if len(candidates) >= max_candidates:
            break

        try:
            # Find nearest ancestor container that has at least one link
            container = btn.find_element(By.XPATH, "./ancestor::div[.//a[@href]][1]")
            anchors = container.find_elements(By.XPATH, ".//a[@href]")

            username = None
            username_anchor = None
            for a in anchors:
                href = a.get_attribute("href") or ""
                u = _extract_username_from_profile_href(href)
                if u:
                    username = u
                    username_anchor = a
                    break

            if not username or username in seen:
                continue

            seen.add(username)
            candidates.append((username, btn, username_anchor))
        except (NoSuchElementException, StaleElementReferenceException):
            continue
        except Exception:
            continue

    return candidates


def _find_explore_people_candidates(driver, max_candidates: int = 50):
    """
    Find follow candidates on Instagram's explore/people page.

    Implementation intentionally reuses the same resilient heuristic as home:
    locate Follow/Follow back buttons and infer the username from nearby profile links.
    """
    return _find_home_follow_candidates(driver, max_candidates=max_candidates)


def _create_follow_entry(apiClient, account_id, user_name: str, source: str, status: str, today_mdy: str):
    """
    Create a follow target entry via the API.
    """
    try:
        apiClient.create_follow_target(
            account_id, user_name, source=source,
            status=status, follow_date=today_mdy
        )
    except Exception:
        # Logging failures shouldn't crash the bot action
        pass


def do_follow_suggested(driver, account, target_count, apiClient, account_id):
    """
    Follow suggested accounts from Instagram's explore/people page

    Args:
        driver: Selenium WebDriver instance
        account: Account username
        target_count: Number of accounts to follow
        apiClient: ApiClient instance for API access
        account_id: Account UUID

    Returns:
        tuple: (followed_count, error_log_string)
    """
    module_errors_log = ""
    followed_count = 0

    try:
        today = date.today()
        today_mdy = today.strftime("%m/%d/%Y")

        # Load database of previously followed accounts from API
        try:
            database_names = list(apiClient.get_all_follow_target_handles(account_id))
        except Exception as e:
            print(f"- [{account}]: [follow][suggested] - Warning: Could not load follow targets: {e}")
            database_names = []

        # Add universal ignore list
        try:
            ignore_list = apiClient.get_ignore_handles()
            database_names.extend(ignore_list)
        except Exception as e:
            print(f"- [{account}]: [follow][suggested] - Warning: Could not load ignore list: {e}")

        print(f"- [{account}]: [follow][suggested] - loaded {len(database_names)} existing entries")

        # ------------------------------------------------------------------
        # Phase A (primary): Explore People
        # ------------------------------------------------------------------
        try:
            driver.get("https://www.instagram.com/explore/people/")
            WebDriverWait(driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
            time.sleep(random.uniform(4, 6))
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e).split("\n")[0]
            module_errors_log += f"{error_type}: explore navigation failed: {error_msg}\n"

        explore_candidates = []
        if followed_count < target_count:
            # Failure signal: no candidates after wait + 1–2 scroll rescans
            for attempt in range(3):
                if followed_count >= target_count:
                    break

                remaining = max(1, target_count - followed_count)
                explore_candidates = _find_explore_people_candidates(driver, max_candidates=max(50, remaining * 4))
                if explore_candidates:
                    break

                # Scroll and rescan
                try:
                    driver.execute_script("window.scrollBy(0, 900);")
                except Exception:
                    pass
                time.sleep(random.uniform(2, 4))

        if explore_candidates:
            print(f"- [{account}]: [follow][suggested] - explore found {len(explore_candidates)} candidate(s)")

            for user_name, follow_button, user_name_anchor in explore_candidates:
                if followed_count >= target_count:
                    break

                try:
                    if user_name in database_names:
                        print(f"- [{account}]: [follow][suggested] - [ prev ] - {user_name}")
                        continue

                    # Hover over username anchor to trigger preview (optional)
                    if user_name_anchor is not None:
                        try:
                            actions = ActionChains(driver)
                            actions.move_to_element(user_name_anchor)
                            actions.perform()
                            time.sleep(random.uniform(1, 3))
                        except Exception:
                            pass

                    page = driver.page_source or ""
                    if ("The account is private" in page) or ("This Account is Private" in page):
                        _create_follow_entry(
                            apiClient, account_id,
                            user_name=user_name,
                            source="suggested[accounts]",
                            status="private",
                            today_mdy=today_mdy,
                        )
                        database_names.append(user_name)
                        print(f"- [{account}]: [follow][suggested] - [private] - {user_name}")
                        continue

                    # Click follow
                    click_success = False
                    try:
                        actions = ActionChains(driver)
                        actions.move_to_element(follow_button)
                        actions.click(follow_button)
                        actions.perform()
                        click_success = True
                    except Exception:
                        try:
                            follow_button.click()
                            click_success = True
                        except Exception:
                            try:
                                driver.execute_script("arguments[0].click();", follow_button)
                                click_success = True
                            except Exception:
                                click_success = False

                    if not click_success:
                        continue

                    followed_count += 1
                    database_names.append(user_name)

                    _create_follow_entry(
                        apiClient, account_id,
                        user_name=user_name,
                        source="suggested[accounts]",
                        status="following",
                        today_mdy=today_mdy,
                    )
                    print(f"- [{account}]: [follow][suggested] - [{followed_count:02d}/{target_count:02d}] - {user_name}")
                    time.sleep(random.uniform(10, 20))

                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    error_type = type(e).__name__
                    error_msg = str(e).split("\n")[0]
                    print(f"- [{account}]: [follow][suggested] - [error] {error_type}: {error_msg[:80]}")
                    module_errors_log += f"{error_type}: {error_msg}\n"
                    continue
        else:
            if followed_count < target_count:
                print(f"- [{account}]: [follow][suggested] - explore returned no users, falling back to home")

        # ------------------------------------------------------------------
        # Phase B (fallback/top-up): Home page Suggested for you
        # ------------------------------------------------------------------
        home_cycles = 0
        max_home_cycles = 2  # one pass + one reload if partial progress was made

        while followed_count < target_count and home_cycles < max_home_cycles:
            home_cycles += 1
            start_count = followed_count

            driver.get("https://www.instagram.com/")
            WebDriverWait(driver, 15).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            time.sleep(random.uniform(4, 6))

            # ------------------------------------------------------------------
            # Primary: existing selector logic (keep as-is)
            # ------------------------------------------------------------------
            user_boxes = driver.find_elements(
                By.XPATH,
                "//div[@data-visualcompletion='loading-state']//ancestor::div[contains(@class, 'x1qnrgzn')]",
            )

            if user_boxes and len(user_boxes) > 0:
                print(f"- [{account}]: [follow][suggested] - found {len(user_boxes)} suggested user(s)")

                for box_index, user_box in enumerate(user_boxes):
                    if followed_count >= target_count:
                        break

                    try:
                        # Get username and follow button status
                        try:
                            user_name_element = user_box.find_element(By.CLASS_NAME, "_aad7")
                            user_status_element = user_box.find_element(By.CLASS_NAME, "_aad6")
                            user_name = user_name_element.text
                            user_status = user_status_element.text

                            if not user_name:
                                continue

                        except Exception:
                            continue

                        # Check if already in database
                        if user_name in database_names:
                            print(f"- [{account}]: [follow][suggested] - [ prev ] - {user_name}")
                            continue

                        # Check if already following
                        if user_status != "Follow":
                            print(f"- [{account}]: [follow][suggested] - [{user_status.lower()}] - {user_name}")
                            continue

                        # Hover over username to trigger profile preview
                        actions = ActionChains(driver)
                        actions.move_to_element(user_name_element)
                        actions.perform()
                        time.sleep(random.uniform(1, 3))

                        # Check for stale element
                        if not user_name_element.text:
                            continue

                        # Check if account is private
                        if "The account is private" in driver.page_source:
                            # Move away from hover
                            profile_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Profile")
                            actions = ActionChains(driver)
                            actions.move_to_element(profile_link)
                            actions.perform()

                            # Log private account via API
                            _create_follow_entry(
                                apiClient, account_id,
                                user_name=user_name,
                                source="suggested[accounts]",
                                status="private",
                                today_mdy=today_mdy,
                            )
                            database_names.append(user_name)

                            print(f"- [{account}]: [follow][suggested] - [private] - {user_name}")

                        else:
                            # Follow the account
                            followed_count += 1

                            actions = ActionChains(driver)
                            actions.move_to_element(user_status_element)
                            actions.click(user_status_element)
                            actions.perform()

                            # Log followed account via API
                            _create_follow_entry(
                                apiClient, account_id,
                                user_name=user_name,
                                source="suggested[accounts]",
                                status="following",
                                today_mdy=today_mdy,
                            )
                            database_names.append(user_name)

                            print(f"- [{account}]: [follow][suggested] - [{followed_count:02d}/{target_count:02d}] - {user_name}")

                            # Delay between follows
                            time.sleep(random.uniform(10, 20))

                    except StaleElementReferenceException:
                        continue

                    except Exception as e:
                        error_type = type(e).__name__
                        error_msg = str(e).split("\n")[0]
                        print(f"- [{account}]: [follow][suggested] - [error] {error_type}: {error_msg[:80]}")
                        module_errors_log += f"{error_type}: {error_msg}\n"
                        continue

            else:
                # ------------------------------------------------------------------
                # Fallback: more resilient candidate finder (only if primary found none)
                # ------------------------------------------------------------------
                remaining = max(1, target_count - followed_count)
                candidates = _find_home_follow_candidates(driver, max_candidates=max(50, remaining * 4))

                if candidates:
                    print(f"- [{account}]: [follow][suggested] - fallback found {len(candidates)} follow candidate(s)")
                else:
                    msg = "[error] no suggested users found"
                    print(f"- [{account}]: [follow][suggested] - {msg}")
                    module_errors_log += f"follow[suggested]: {msg}\n"
                    return followed_count, module_errors_log

                for user_name, follow_button, user_name_anchor in candidates:
                    if followed_count >= target_count:
                        break

                    try:
                        if user_name in database_names:
                            print(f"- [{account}]: [follow][suggested] - [ prev ] - {user_name}")
                            continue

                        if user_name_anchor is not None:
                            try:
                                actions = ActionChains(driver)
                                actions.move_to_element(user_name_anchor)
                                actions.perform()
                                time.sleep(random.uniform(1, 3))
                            except Exception:
                                pass

                        page = driver.page_source or ""
                        if ("The account is private" in page) or ("This Account is Private" in page):
                            _create_follow_entry(
                                apiClient, account_id,
                                user_name=user_name,
                                source="suggested[accounts]",
                                status="private",
                                today_mdy=today_mdy,
                            )
                            database_names.append(user_name)
                            print(f"- [{account}]: [follow][suggested] - [private] - {user_name}")
                        else:
                            followed_count += 1

                            try:
                                actions = ActionChains(driver)
                                actions.move_to_element(follow_button)
                                actions.click(follow_button)
                                actions.perform()
                            except Exception:
                                try:
                                    follow_button.click()
                                except Exception:
                                    try:
                                        driver.execute_script("arguments[0].click();", follow_button)
                                    except Exception:
                                        followed_count -= 1
                                        continue

                            _create_follow_entry(
                                apiClient, account_id,
                                user_name=user_name,
                                source="suggested[accounts]",
                                status="following",
                                today_mdy=today_mdy,
                            )
                            database_names.append(user_name)
                            print(f"- [{account}]: [follow][suggested] - [{followed_count:02d}/{target_count:02d}] - {user_name}")
                            time.sleep(random.uniform(10, 20))

                    except StaleElementReferenceException:
                        continue

                    except Exception as e:
                        error_type = type(e).__name__
                        error_msg = str(e).split("\n")[0]
                        print(f"- [{account}]: [follow][suggested] - [error] {error_type}: {error_msg[:80]}")
                        module_errors_log += f"{error_type}: {error_msg}\n"
                        continue

            # Loop will reload home and continue if still under target
        
        if followed_count < target_count:
            if followed_count == 0:
                msg = "[error] no suggested users found"
            else:
                msg = "[error] limited suggested users found"
            print(f"- [{account}]: [follow][suggested] - {msg} ({followed_count}/{target_count})")
            module_errors_log += f"follow[suggested]: {msg} ({followed_count}/{target_count})\n"
        else:
            print(f"- [{account}]: [follow][suggested] - completed {followed_count} follow(s)")

    except Exception as e:
        # Simplified error output
        error_type = type(e).__name__
        error_msg = str(e).split('\n')[0]
        print(f"- [{account}]: [follow][suggested] - [FATAL ERROR] {error_type}: {error_msg[:100]}")
        module_errors_log += f"{error_type}: {error_msg}\n"
    
    return followed_count, module_errors_log


