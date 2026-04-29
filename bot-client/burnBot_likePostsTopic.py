# burnBot_likePostsTopic.py
# Likes posts from Instagram topic/keyword search results.
# Topics are read from the account settings row on Google Drive (Column AO, index 40),
# supplied as a comma-separated list of hashtags or topic names (e.g. "beer, craft beer, brewing").
# Each topic is opened via Instagram's in-app Search UI, then posts are liked until the target is reached.

import builtins as _builtins
from burnBot_imports import *
from burnBot_utils import process_exception
from burnBot_accountSession_setup import is_bot_debug_enabled
import random
import time

_p = _builtins.print  # set per-call by do_like_posts_topic; safe because sessions run sequentially


def _normalize_post_path(post_url):
    """Return a stable /p/... path for matching result links."""
    if not post_url:
        return ""

    cleaned_url = post_url.strip()
    if "instagram.com" in cleaned_url:
        cleaned_url = cleaned_url.split("instagram.com", 1)[1]

    cleaned_url = cleaned_url.split("?", 1)[0].split("#", 1)[0]
    if not cleaned_url.startswith("/"):
        cleaned_url = f"/{cleaned_url}"

    if cleaned_url.startswith("/p/") and not cleaned_url.endswith("/"):
        cleaned_url = f"{cleaned_url}/"

    return cleaned_url


def _extract_username_from_href(href):
    """Extract an Instagram username from a profile-style href."""
    if not href:
        return ""

    cleaned_href = href.strip()
    if "instagram.com" in cleaned_href:
        cleaned_href = cleaned_href.split("instagram.com", 1)[1]

    cleaned_href = cleaned_href.split("?", 1)[0].split("#", 1)[0]
    if not cleaned_href.startswith("/"):
        cleaned_href = f"/{cleaned_href}"

    path_parts = [part for part in cleaned_href.split("/") if part]
    if len(path_parts) != 1:
        return ""

    username = path_parts[0].strip()
    if not username:
        return ""

    reserved_paths = {
        "about",
        "accounts",
        "ads",
        "api",
        "challenge",
        "developer",
        "direct",
        "explore",
        "graphql",
        "p",
        "reel",
        "reels",
        "stories",
        "tags",
    }
    if username.lower() in reserved_paths:
        return ""

    allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._"
    if any(ch not in allowed_chars for ch in username):
        return ""

    return username


def _get_post_author_username(article):
    """Find the post owner's username from profile links inside the opened post."""
    candidate_locators = [
        ".//header//a[@href]",
        ".//a[@href]",
    ]

    for locator in candidate_locators:
        try:
            anchor_elements = article.find_elements(By.XPATH, locator)
        except Exception:
            continue

        for anchor in anchor_elements:
            try:
                href = anchor.get_attribute("href") or ""
                username = _extract_username_from_href(href)
                if not username:
                    continue

                anchor_text = " ".join((anchor.text or "").split())
                if locator == ".//header//a[@href]":
                    return username

                if anchor_text and username.lower() in anchor_text.lower():
                    return username

                has_profile_image = len(anchor.find_elements(By.XPATH, ".//img")) > 0
                if has_profile_image:
                    return username
            except StaleElementReferenceException:
                continue
            except Exception:
                continue

    return "unknown"


def _open_post_from_results(driver, account, post_url):
    """
    Open a result tile with a real click so Instagram keeps the user in the
    search-results flow instead of forcing a direct page load.
    """
    post_path = _normalize_post_path(post_url)
    if not post_path:
        return False

    result_locator = (
        By.XPATH,
        f"//a[contains(@href, '{post_path}') and not(contains(@href, '/liked_by'))]"
    )

    try:
        result_link = WebDriverWait(driver, 10).until(
            lambda d: next(
                (elem for elem in d.find_elements(*result_locator) if elem.is_displayed()),
                None
            )
        )
    except Exception:
        if is_bot_debug_enabled():
            _p(f"- [{account}]: [like][topics][debug] - could not find result tile for [{post_path}]")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", result_link)
        time.sleep(random.uniform(1, 2))
    except Exception:
        pass

    clicked = False
    try:
        actions = ActionChains(driver)
        actions.move_to_element(result_link)
        actions.pause(0.4)
        actions.click(result_link)
        actions.perform()
        clicked = True
    except Exception:
        pass

    if not clicked:
        try:
            driver.execute_script("arguments[0].click();", result_link)
            clicked = True
        except Exception:
            pass

    if not clicked:
        if is_bot_debug_enabled():
            _p(f"- [{account}]: [like][topics][debug] - result tile click failed for [{post_path}]")
        return False

    try:
        WebDriverWait(driver, 12).until(
            lambda d: (
                post_path in ((d.current_url or "").split("instagram.com")[-1].split("?", 1)[0])
                and len(d.find_elements(By.TAG_NAME, "article")) > 0
            )
        )
        time.sleep(random.uniform(2, 3))
        return True
    except Exception:
        if is_bot_debug_enabled():
            _p(f"- [{account}]: [like][topics][debug] - post did not finish opening for [{post_path}]")
        return False


def _close_open_post(driver, account, results_url):
    """Close an opened result and return to the search grid."""
    try:
        body = driver.find_element(By.TAG_NAME, "body")
    except Exception:
        body = None

    for _ in range(2):
        try:
            if body:
                body.send_keys(Keys.ESCAPE)
            else:
                driver.switch_to.active_element.send_keys(Keys.ESCAPE)
        except Exception:
            pass

        try:
            WebDriverWait(driver, 6).until(
                lambda d: (
                    "/explore/search/keyword/" in (d.current_url or "")
                    and len(d.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")) > 0
                )
            )
            time.sleep(random.uniform(1, 2))
            return True
        except Exception:
            pass

    close_button_locators = [
        (By.XPATH, "//div[@role='dialog']//*[@aria-label='Close']"),
        (By.XPATH, "//div[@role='dialog']//*[@role='button'][.//*[local-name()='svg' and @aria-label='Close']]"),
    ]

    for by, locator in close_button_locators:
        try:
            close_button = WebDriverWait(driver, 4).until(
                lambda d: next(
                    (elem for elem in d.find_elements(by, locator) if elem.is_displayed()),
                    None
                )
            )
            driver.execute_script("arguments[0].click();", close_button)
            WebDriverWait(driver, 6).until(
                lambda d: (
                    "/explore/search/keyword/" in (d.current_url or "")
                    and len(d.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")) > 0
                )
            )
            time.sleep(random.uniform(1, 2))
            return True
        except Exception:
            continue

    try:
        if "/p/" in (driver.current_url or "") and results_url:
            driver.back()
            WebDriverWait(driver, 10).until(
                lambda d: (
                    results_url in (d.current_url or "")
                    or (
                        "/explore/search/keyword/" in (d.current_url or "")
                        and len(d.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")) > 0
                    )
                )
            )
            time.sleep(random.uniform(1, 2))
            return True
    except Exception:
        pass

    if is_bot_debug_enabled():
        print(f"- [{account}]: [like][topics][debug] - could not return to results grid")
    return False


def _open_topic_search_results(driver, account, topic):
    """
    Open Instagram search UI, search for a topic, and land on the
    keyword results page. Direct URL loads have proven unreliable for this flow.
    """
    search_query = topic.strip()
    if not search_query:
        return False

    try:
        driver.get("https://www.instagram.com/")
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(random.uniform(2, 4))

        search_clicked = False
        search_locators = [
            (By.XPATH, "//a[contains(@href,'/explore/search')]"),
            (By.XPATH, "//a[@href='/explore/' and (.//*[normalize-space()='Search'] or @aria-label='Search')]"),
            (By.XPATH, "//span[normalize-space()='Search']/ancestor::*[self::a or self::button or @role='link' or @tabindex][1]"),
            (By.XPATH, "//*[self::a or self::div or self::button][@aria-label='Search']"),
            (By.XPATH, "//*[@role='link' and @aria-label='Search']"),
            (By.XPATH, "//*[self::a or self::div or self::button][.//*[normalize-space()='Search'] or normalize-space()='Search']"),
        ]

        for by, locator in search_locators:
            try:
                candidates = driver.find_elements(by, locator)
                for candidate in candidates:
                    if candidate.is_displayed():
                        driver.execute_script("arguments[0].click();", candidate)
                        search_clicked = True
                        break
                if search_clicked:
                    break
            except Exception:
                continue

        if not search_clicked:
            try:
                search_clicked = driver.execute_script("""
                    const searchSpan = Array.from(document.querySelectorAll('span'))
                        .find(el => (el.textContent || '').trim() === 'Search');
                    if (searchSpan) {
                        const clickable = searchSpan.closest('a, button, [role="link"], [tabindex]');
                        if (clickable) {
                            clickable.click();
                            return true;
                        }
                    }
                    return false;
                """)
            except Exception:
                search_clicked = False

        if not search_clicked:
            try:
                driver.get("https://www.instagram.com/explore/search/")
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(random.uniform(2, 4))
                search_clicked = True
                if is_bot_debug_enabled():
                    _p(f"- [{account}]: [like][topics] - using direct search page fallback for [{topic}]")
            except Exception:
                _p(f"- [{account}]: [like][topics] - [error] could not open search for [{topic}]")
                return False

        search_input = None

        try:
            search_input = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((
                    By.XPATH,
                    "//input[@aria-label='Search input' and @placeholder='Search' and @type='text']"
                ))
            )
        except Exception:
            search_input = None

        input_locators = [
            (By.XPATH, "//input[@aria-label='Search input']"),
            (By.XPATH, "//input[@placeholder='Search']"),
            (By.XPATH, "//input[contains(@aria-label,'Search')]"),
            (By.XPATH, "//input[@type='text']"),
            (By.XPATH, "//textarea[contains(@aria-label,'Search') or @placeholder='Search']"),
            (By.XPATH, "//*[@role='searchbox']"),
            (By.XPATH, "//*[@role='textbox']"),
            (By.XPATH, "//*[@contenteditable='true']"),
            (By.XPATH, "//*[contains(@aria-label,'Search') and (@role='textbox' or @contenteditable='true')]"),
        ]

        if not search_input:
            for by, locator in input_locators:
                try:
                    candidates = driver.find_elements(by, locator)
                    visible_candidates = [elem for elem in candidates if elem.is_displayed()]
                    if visible_candidates:
                        search_input = visible_candidates[0]
                        break
                except Exception:
                    continue

        if not search_input:
            try:
                search_input = driver.execute_script("""
                    const selectors = [
                        "input[aria-label='Search input']",
                        "input[placeholder='Search']",
                        "input[aria-label*='Search']",
                        "textarea[aria-label*='Search']",
                        "[role='searchbox']",
                        "[role='textbox']",
                        "[contenteditable='true']",
                        "[aria-label*='Search']"
                    ];
                    for (const selector of selectors) {
                        const elements = Array.from(document.querySelectorAll(selector));
                        const visible = elements.find(el => {
                            const style = window.getComputedStyle(el);
                            const rect = el.getBoundingClientRect();
                            return style && style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
                        });
                        if (visible) {
                            return visible;
                        }
                    }
                    return null;
                """)
            except Exception:
                search_input = None

        if not search_input:
            _p(f"- [{account}]: [like][topics] - [error] search box not found for [{topic}]")
            return False

        try:
            search_input.click()
        except Exception:
            pass

        try:
            active_role = (search_input.get_attribute("role") or "").lower()
            is_editable = (search_input.get_attribute("contenteditable") or "").lower() == "true"

            if is_editable or active_role in ["textbox", "searchbox"]:
                search_input.send_keys(Keys.CONTROL, "a")
                search_input.send_keys(Keys.BACKSPACE)
            else:
                search_input.send_keys(Keys.CONTROL, "a")
                search_input.send_keys(Keys.DELETE)
        except Exception:
            try:
                search_input.clear()
            except Exception:
                pass

        search_input.send_keys(search_query)
        time.sleep(random.uniform(3, 5))

        keyword_clicked = False
        normalized_query = " ".join(search_query.lower().split())

        keyword_result_locators = [
            (
                By.XPATH,
                f"//a[contains(@href, '/explore/search/keyword/')][.//span[normalize-space()=\"{search_query}\"]]"
            ),
            (
                By.XPATH,
                "//a[contains(@href, '/explore/search/keyword/')]"
            ),
        ]

        for by, locator in keyword_result_locators:
            try:
                keyword_candidates = WebDriverWait(driver, 15).until(
                    lambda d: [elem for elem in d.find_elements(by, locator) if elem.is_displayed()]
                )
                if keyword_candidates:
                    if len(keyword_candidates) > 1:
                        for candidate in keyword_candidates:
                            try:
                                candidate_text = " ".join((candidate.text or "").lower().split())
                                if candidate_text and normalized_query in candidate_text:
                                    driver.execute_script("arguments[0].click();", candidate)
                                    keyword_clicked = True
                                    break
                            except Exception:
                                continue
                    if not keyword_clicked:
                        driver.execute_script("arguments[0].click();", keyword_candidates[0])
                        keyword_clicked = True
                    if keyword_clicked:
                        break
            except Exception:
                continue

        if not keyword_clicked:
            search_input.send_keys(Keys.ENTER)
            time.sleep(2)
            search_input.send_keys(Keys.ENTER)

        WebDriverWait(driver, 15).until(
            lambda d: (
                "/explore/search/keyword/" in (d.current_url or "")
                or len(d.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")) > 0
            )
        )
        time.sleep(random.uniform(4, 6))
        return True

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e).split("\n")[0]
        print(f"- [{account}]: [like][topics] - [error] search failed for [{topic}] - {error_type}: {error_msg[:80]}")
        return False


def do_like_posts_topic(driver, account, target_count, apiClient=None, account_id=None, topics=None, _print=None):
    global _p
    _p = _print if _print is not None else _builtins.print
    """
    Like posts from Instagram topic/hashtag pages.

    Args:
        driver:       Selenium WebDriver instance
        account:      Account name (for logging)
        target_count: Number of posts to like
        apiClient:    Optional ApiClient instance for ignore list access
        account_id:   Account UUID (unused here, kept for consistent interface)
        topics:       Comma-separated string of hashtags/topics (e.g. "beer, craft beer").
                      Leading '#' characters are stripped automatically.

    Returns:
        tuple: (likes_performed, errors_log)
    """
    likes_performed = 0
    moduleErrorsLog = ""

    # Parse topic list
    topic_list = []
    if topics:
        for t in topics.split(","):
            t = t.strip().lstrip("#")
            if t:
                topic_list.append(t)

    if not topic_list:
        msg = "[error] no topics configured for post[topics] action"
        print(f"- [{account}]: [like][topics] - {msg}")
        moduleErrorsLog += f"like[topics]: {msg}\n"
        return 0, moduleErrorsLog

    # Load like_sponsored setting from API (suggested posts don't appear on hashtag pages)
    _user_cfg = apiClient.get_user_config() if apiClient else {}
    like_sponsored = _user_cfg.get('like_sponsored', True)

    # Load ignore list if available
    ignore_list = []
    if apiClient:
        try:
            ignore_list = apiClient.get_ignore_handles()
            if ignore_list and is_bot_debug_enabled():
                _p(f"- [{account}]: [like][topics] - loaded {len(ignore_list)} ignored account(s)")
        except Exception as e:
            _p(f"- [{account}]: [like][topics] - Warning: Could not load ignore list: {e}")

    target_formatted = f"{target_count:02d}"
    processed_urls = set()  # Track post URLs to avoid double-liking across topics

    try:
        for topic in topic_list:
            if likes_performed >= target_count:
                break

            _p(f"- [{account}]: [like][topics] - searching topic [{topic}]")

            if not _open_topic_search_results(driver, account, topic):
                moduleErrorsLog += f"like[topics]: [error] could not open search results for [{topic}]\n"
                continue

            max_posts_per_topic = max(target_count * 3, 30)  # scan more than target to find unliked posts
            posts_scanned = 0
            scrolls = 0
            max_scrolls = 10

            while likes_performed < target_count and scrolls < max_scrolls:
                if scrolls == 0:
                    try:
                        WebDriverWait(driver, 12).until(
                            lambda d: (
                                len(d.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")) > 0
                                or len(d.find_elements(By.XPATH, "//*[contains(normalize-space(),'See more')]")) > 0
                            )
                        )
                    except Exception:
                        pass

                # Find post thumbnail links on the topic page (grid layout) and extract
                # hrefs into a plain list now. The live DOM can still change after each
                # modal open/close cycle, so we avoid holding thumbnail elements directly.
                post_links = driver.find_elements(
                    By.XPATH,
                    "//a[contains(@href, '/p/') and not(contains(@href, '/p/liked_by'))]"
                )

                new_link_urls = []
                for lnk in post_links:
                    try:
                        href = lnk.get_attribute("href")
                        if href and href not in processed_urls:
                            new_link_urls.append(href)
                    except StaleElementReferenceException:
                        continue

                if not new_link_urls:
                    if scrolls == 0:
                        _p(f"- [{account}]: [like][topics] - no posts found for topic [{topic}]")
                    break

                for post_url in new_link_urls:
                    if likes_performed >= target_count or posts_scanned >= max_posts_per_topic:
                        break

                    if post_url in processed_urls:
                        continue

                    processed_urls.add(post_url)
                    posts_scanned += 1

                    results_url = driver.current_url
                    post_opened = False

                    try:
                        post_opened = _open_post_from_results(driver, account, post_url)
                        if not post_opened:
                            if is_bot_debug_enabled():
                                _p(f"- [{account}]: [like][topics][ skip ] - could not open [{post_url}] from results")
                            continue

                        article = WebDriverWait(driver, 8).until(
                            EC.presence_of_element_located((By.TAG_NAME, "article"))
                        )
                        article_account = _get_post_author_username(article)

                        # Check ignore list
                        if article_account in ignore_list:
                            display_name = article_account[:15] if len(article_account) > 15 else article_account
                            _p(f"- [{account}]: [like][topics][ skip ] - [{display_name}] - [ignored]")
                            continue

                        # Skip sponsored posts if like_sponsored is disabled
                        if not like_sponsored:
                            try:
                                page_inner_text = driver.execute_script("return document.body.innerText || ''")
                                is_ad = 'Sponsored' in page_inner_text
                                if not is_ad:
                                    is_ad = bool(driver.find_elements(
                                        By.XPATH, "//*[contains(@href,'/ads/about')]"
                                    ))
                                if is_ad:
                                    display_name = article_account[:15] if len(article_account) > 15 else article_account
                                    _p(f"- [{account}]: [like][topics][ skip ] - [{display_name}] - [sponsored]")
                                    continue
                            except Exception:
                                pass

                        # Find like button
                        try:
                            like_button = WebDriverWait(article, 8).until(
                                EC.presence_of_element_located((
                                    By.XPATH,
                                    ".//*[@role='button'][.//*[local-name()='svg' and @aria-label='Like']]"
                                ))
                            )

                            like_status = ""
                            try:
                                like_icon = like_button.find_element(By.XPATH, ".//*[local-name()='svg' and @aria-label='Like']")
                                like_status = like_icon.get_attribute("aria-label") or ""
                            except Exception:
                                like_status = ""

                            if like_status == "Like":
                                display_name = article_account[:15] if len(article_account) > 15 else article_account
                                try:
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", like_button)
                                    time.sleep(1)
                                except Exception:
                                    pass

                                clicked = False
                                try:
                                    actions = ActionChains(driver)
                                    actions.move_to_element(like_button)
                                    actions.pause(0.5)
                                    actions.click(like_button)
                                    actions.perform()
                                    clicked = True
                                except Exception:
                                    pass

                                if not clicked:
                                    try:
                                        driver.execute_script("arguments[0].click();", like_button)
                                        clicked = True
                                    except Exception:
                                        pass

                                if clicked:
                                    try:
                                        WebDriverWait(article, 6).until(
                                            lambda a: len(a.find_elements(
                                                By.XPATH,
                                                ".//*[@role='button'][.//*[local-name()='svg' and @aria-label='Unlike']]"
                                            )) > 0
                                        )
                                        likes_performed += 1
                                        count_formatted = f"{likes_performed:02d}"
                                        _p(f"- [{account}]: [like][topics][{count_formatted}/{target_formatted}] - [{display_name}] - [{topic}]")
                                        time.sleep(random.randint(6, 8))
                                    except Exception:
                                        if is_bot_debug_enabled():
                                            _p(f"- [{account}]: [like][topics][ skip ] - [{display_name}] - [like state did not change]")
                                elif is_bot_debug_enabled():
                                    _p(f"- [{account}]: [like][topics][ skip ] - [{display_name}] - [like click failed]")
                            else:
                                if is_bot_debug_enabled():
                                    display_name = article_account[:15] if len(article_account) > 15 else article_account
                                    state_label = like_status if like_status else "no like control"
                                    _p(f"- [{account}]: [like][topics][-----] - [{display_name}] - [{topic}] - [{state_label}]")

                        except (NoSuchElementException, TimeoutException):
                            pass
                        except StaleElementReferenceException:
                            pass

                    except Exception as e:
                        error_type = type(e).__name__
                        msg = str(e).split('\n')[0]
                        if is_bot_debug_enabled():
                            _p(f"- [{account}]: [like][topics] - [error] {error_type}: {msg[:80]}")
                        moduleErrorsLog += f"like[topics]: {error_type}: {msg}\n"
                        continue
                    finally:
                        if post_opened:
                            _close_open_post(driver, account, results_url)

                # Re-open the search results page and scroll to load more posts if still needed
                if likes_performed < target_count:
                    if not _open_topic_search_results(driver, account, topic):
                        moduleErrorsLog += f"like[topics]: [error] could not refresh search results for [{topic}]\n"
                        break
                    driver.execute_script("window.scrollBy(0, 900);")
                    time.sleep(random.uniform(2, 3))
                    scrolls += 1
                else:
                    break

        # Final status
        if likes_performed < target_count:
            if likes_performed == 0:
                msg = "[error] no topic posts liked"
            else:
                msg = "[error] limited topic posts liked"
            _p(f"- [{account}]: [like][topics] - {msg} ({likes_performed}/{target_count})")
            moduleErrorsLog += f"like[topics]: {msg} ({likes_performed}/{target_count})\n"
        else:
            _p(f"- [{account}]: [like][topics] - complete - {likes_performed} posts liked")

    except Exception as error:
        noteError = f"do_like_posts_topic catch all: {str(error)}"
        moduleErrorsLog += process_exception(True, noteError, True, False)

    return likes_performed, moduleErrorsLog
