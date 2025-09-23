
from lib import *



def click_if_next_button(driver, timeout=4):
    time.sleep(0.3)

    try:
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
            print("[next] switched to latest window")
    except Exception:
        pass

    XPATHS = [
        # VI
        "//*[self::button or @role='button'][.//span[normalize-space()='Tiếp theo'] or normalize-space()='Tiếp theo']",
        "//*[@id='passwordNext']",
        # EN (case-insensitive)
        "//*[self::button or @role='button'][translate(normalize-space(.),'NEXT','next')='next']",
        "//*[contains(translate(@aria-label,'NEXT','next'),'next')]",
        "//*[@id='next' or @id='identifierNext' or @id='passwordNext']",

        "//*[self::button or @role='button'][translate(normalize-space(.),'CONTINUE','continue')='continue']",
        "//*[contains(translate(@aria-label,'CONTINUE','continue'),'continue')]",
    ]

    def try_click(el):
        # đưa vào tầm nhìn
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", el)
            time.sleep(0.1)
        except Exception:
            pass
        # 3 kiểu click
        for clicker in (
            lambda e: e.click(),
            lambda e: ActionChains(driver).move_to_element(e).pause(0.05).click().perform(),
            lambda e: driver.execute_script("arguments[0].click();", e),
        ):
            try:
                clicker(el)
                return True
            except Exception:
                continue
        return False

    def search_and_click_in_current_context():
        # chờ page state ổn định một nhịp (tránh overlay)
        try:
            WebDriverWait(driver, 3).until(lambda d: d.execute_script("return document.readyState") in ("interactive","complete"))
        except Exception:
            pass

        # nếu có overlay che, chờ nó biến mất (best-effort)
        # (bỏ qua nếu không có overlay selector cụ thể)

        for xp in XPATHS:
            try:
                el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xp)))
                if try_click(el):
                    print(f"[next] clicked via {xp}")
                    return True
                else:
                    print(f"[next] found but could not click: {xp}")
            except Exception:
                continue
        return False

    # 3) Thử ở document chính
    if search_and_click_in_current_context():
        return True

    # 4) Thử trong tất cả iframe
    try:
        frames = driver.find_elements(By.TAG_NAME, "iframe")
    except Exception:
        frames = []

    for idx, fr in enumerate(frames):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(fr)
            if search_and_click_in_current_context():
                driver.switch_to.default_content()
                return True
        except Exception:
            continue

    driver.switch_to.default_content()
    print("[next] not found/clickable -> return False")
    return False

def scroll_modal_and_click_continue(driver, timeout=8):
    """
    Scroll bên trong modal/inner container ở giữa màn hình (nếu có), 
    rồi bấm 'Tiếp tục' / 'Continue' bên trong modal đó.
    Trả về True nếu bấm được, False nếu không tìm thấy.
    """
    import time
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    # 1) Tìm container cuộn ở giữa màn hình (scrollHeight > clientHeight và overflow-y không ẩn)
    get_center_scrollable_js = r"""
    const cx = Math.floor(window.innerWidth/2), cy = Math.floor(window.innerHeight/2);
    const els = document.elementsFromPoint(cx, cy);
    function isScrollable(el) {
      if (!el || el === document.documentElement) return false;
      const style = getComputedStyle(el);
      const canScroll = el.scrollHeight - el.clientHeight > 10; // có thanh cuộn theo trục dọc
      const overflowY = style.overflowY;
      const okOverflow = overflowY && overflowY !== 'visible' && overflowY !== 'hidden';
      return canScroll && okOverflow;
    }
    // Ưu tiên phần tử có role=dialog / aria-modal
    let candidates = els.filter(el => el.getAttribute && (el.getAttribute('role') === 'dialog' || el.getAttribute('aria-modal') === 'true'));
    if (!candidates.length) candidates = els;
    const found = candidates.find(isScrollable) || els.find(isScrollable);
    return found || null;
    """

    try:
        modal = driver.execute_script(get_center_scrollable_js)
    except Exception:
        modal = None

    # Nếu không tìm được modal scrollable, fallback: dùng body như cũ
    scroll_target = modal if modal else driver.execute_script("return document.scrollingElement || document.body;")

    # 2) Scroll container đến đáy (tăng dần, phòng trường hợp cần tải lazy/enable button)
    try:
        driver.execute_script("""
        const el = arguments[0];
        if (!el) return;
        el.scrollTop = 0;
        """, scroll_target)

        last = -1
        for _ in range(20):  # tối đa ~20 bước
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scroll_target)
            time.sleep(0.25)
            cur = driver.execute_script("return arguments[0].scrollTop;", scroll_target)
            if cur == last:  # không tăng nữa
                break
            last = cur
    except Exception:
        pass

    # 3) Tìm nút 'Tiếp tục / Continue' BÊN TRONG modal (nếu có modal)
    XPATH_CONT = (
        ".//button[normalize-space()='Tiếp tục'] | .//button/span[normalize-space()='Tiếp tục']/.. | "
        ".//button[normalize-space()='Continue'] | .//button/span[normalize-space()='Continue']/.. | "
        ".//*[@role='button' and (normalize-space()='Tiếp tục' or normalize-space()='Continue')]"
    )
    try:
        if modal:
            # tìm bên trong modal
            cont_btn = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, XPATH_CONT)),
                message="Cannot find Continue in modal"
            )

            cont_el = driver.execute_script("""
                const root = arguments[0];
                return root.querySelector("button:has(span:empty)") || root.querySelector("button");
            """, modal)
            # Nếu JS trên không chuẩn cho mọi DOM, dùng cách tìm tương đối:
            if not cont_el:
                # fallback: tìm theo XPath tương đối thủ công
                from selenium.webdriver.remote.webelement import WebElement
                # Lấy tất cả candidate bằng JS cho chắc:
                cont_el = driver.execute_script("""
                    const root = arguments[0];
                    const q = (sel) => root.querySelector(sel);
                    const trySelectors = [
                      "button:has(span:contains('Tiếp tục'))",
                      "button:has(span:contains('Continue'))",
                    ];
                    for (const s of trySelectors) {
                      try {
                        const el = root.querySelector("button");
                        if (el) return el;
                      } catch {}
                    }
                    return null;
                """, modal)
            # Nếu vẫn không có, dùng global XPath nhưng scroll modal xong thường có thể click trực tiếp:
            if not cont_el:
                cont_el = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH,
                        "//button[normalize-space()='Tiếp tục'] | //button/span[normalize-space()='Tiếp tục']/.. | "
                        "//button[normalize-space()='Continue'] | //button/span[normalize-space()='Continue']/.."
                    ))
                )

            # Đưa nút vào giữa viewport và click
            driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", cont_el)
            time.sleep(0.3)
            try:
                cont_el.click()
            except Exception:
                driver.execute_script("arguments[0].click();", cont_el)

            print("Đã click nút Tiếp tục / Continue trong modal")
            return True

        else:
            # Không có modal: tìm nút ở document như cũ
            cont_btn = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//button[normalize-space()='Tiếp tục'] | //button/span[normalize-space()='Tiếp tục']/.. | "
                    "//button[normalize-space()='Continue'] | //button/span[normalize-space()='Continue']/.."
                ))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cont_btn)
            time.sleep(0.3)
            cont_btn.click()
            print("Đã click nút Tiếp tục / Continue (document)")
            return True

    except Exception:
        print("Không tìm thấy hoặc không click được nút Tiếp tục / Continue trong modal/document")
        return False


def login_google(
    email,
    password,
    max_retries=2,
    manual_captcha_wait=90,
    expected_post_login_url_contains="labs.google/flow",
    keep_open=False,
    driver = None,
):
    
    retry_count = 0

    while retry_count <= max_retries:
        try:
            # --- Chrome options / anti-detection tweaks ---
            chrome_options = Options()
            chrome_options.page_load_strategy = "eager"
            # chrome_options.add_argument("--headless=new")  # để debug thì comment
            chrome_options.add_argument("--incognito")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(60)

            try:
                driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                })
            except Exception:
                try:
                    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                except Exception:
                    pass

            print(f"[{email}] Login attempt {retry_count + 1}/{max_retries + 1}")

            # --- Navigate to target page ---
            driver.get("https://labs.google/flow/about")
            time.sleep(random.uniform(2.0, 4.0))

            # Dismiss cookie/consent nếu có
            try:
                cookie_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'i agree')]"
                    ))
                )
                cookie_btn.click()
                print(f"[{email}] Dismissed cookie/consent banner")
            except Exception:
                pass

            # Click "Create with Flow"
            try:
                create_btn = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'create with flow')]"
                    ))
                )
                ActionChains(driver).move_to_element(create_btn).click().perform()
                print(f"[{email}] Clicked 'Create with Flow'")
            except Exception as e:
                print(f"[{email}] Could not find 'Create with Flow' button reliably: {e}")

            # If popup opens in new window, switch
            original_window = driver.current_window_handle
            try:
                WebDriverWait(driver, 8).until(EC.number_of_windows_to_be(2))
                for wh in driver.window_handles:
                    if wh != original_window:
                        driver.switch_to.window(wh)
                        print(f"[{email}] Switched to popup window")
                        break
            except Exception:
                pass

            # Chờ đến trang accounts.google.com
            WebDriverWait(driver, 20).until(EC.url_contains("accounts.google.com"))
            print(f"[{email}] Reached Google login page")

            # --- Nhập email ---
            email_field = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "identifierId"))
            )
            email_field.clear()
            time.sleep(random.uniform(0.2, 0.6))
            email_field.send_keys(email)

            # Next
            nxt = None
            try:
                nxt = driver.find_element(By.ID, "identifierNext")
            except Exception:
                try:
                    nxt = driver.find_element(By.XPATH, "//button/span[text()='Next']/..")
                except Exception:
                    pass
            if nxt:
                nxt.click()
            else:
                print(f"[{email}] Cannot find identifierNext button; continuing anyway.")

            # --- Ô password (nhiều fallback) ---
            password_field = None
            try:
                password_field = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.NAME, "Passwd"))
                )
            except Exception:
                try:
                    password_field = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.NAME, "password"))
                        )
                except Exception:
                        try:
                            password_field = WebDriverWait(driver, 20).until(
                                EC.element_to_be_clickable((By.XPATH, "//input[@type='password']"))
                            )
                        except Exception:
                            pass

            if not password_field:
                print(f"[{email}] Password field not found — saving page source and aborting this attempt.")
                save_page_source(driver, f"pw_field_not_found_{email}")
                raise RuntimeError("Password field not found")

            driver.execute_script("arguments[0].scrollIntoView(true);", password_field)
            time.sleep(random.uniform(0.4, 1.2))
            ActionChains(driver).move_to_element(password_field).click().perform()

            for ch in password:
                password_field.send_keys(ch)
                time.sleep(random.uniform(0.04, 0.16))

            # Next password
            try:
                pwd_next = driver.find_element(By.ID, "passwordNext")
                pwd_next.click()
            except Exception:
                password_field.send_keys("\n")

            time.sleep(random.uniform(2.0, 4.0))

            # --- CAPTCHA ---
            if is_captcha_present(driver):
                print(f"[{email}] CAPTCHA/recaptcha detected. Please solve it manually.")
                save_page_source(driver, f"captcha_{email}")
                waited = 0
                while waited < manual_captcha_wait:
                    time.sleep(1)
                    waited += 1
                try:
                    driver.find_element(By.ID, "passwordNext").click()
                except Exception:
                    pass

            time.sleep(1.0)
            need_verify = click_if_next_button(driver)
            print(f"Cần verify: [{need_verify}]")
            if need_verify:
                scroll_modal_and_click_continue(driver)
            else:
                print("Không có nút Tiếp theo, bỏ qua bước Tiếp tục")

            # --- Lỗi login (hiển thị) ---
            err_text = detect_google_login_error(driver)
            if err_text:
                print(f"[{email}] Detected login error message: {err_text}")
                save_page_source(driver, f"login_error_{email}")
                if retry_count < max_retries:
                    retry_count += 1
                    if not keep_open and driver:
                        driver.quit()
                        driver = None
                    print(f"[{email}] Retrying (login error).")
                    time.sleep(random.uniform(2, 5))
                    continue
                else:
                    print(f"[{email}] Max retries reached after login error. Aborting.")
                    return False

            
            # --- 2FA / verify ---
            page_lower = driver.page_source.lower()
            if ("2-step" in page_lower) or ("2-step verification" in page_lower) or ("verify it's you" in page_lower) or ("verify your identity" in page_lower) or ("phone" in page_lower and "verify" in page_lower):
                print(f"[{email}] 2FA/additional verification required.")
                save_page_source(driver, f"2fa_required_{email}")
                return False

            # --- Chờ redirect về trang đích sau khi login ---
            try:
                WebDriverWait(driver, 30).until(EC.url_contains(expected_post_login_url_contains))
                print(f"[{email}] Login successful and returned to expected page.")
                time.sleep(6)
                #KHÔNG quit nếu keep_open=True
                if not keep_open and driver:
                    driver.quit()
                    driver = None
                return True
            except Exception:
                # thử nhận diện trạng thái đã login qua "sign out"
                try:
                    if "sign out" in driver.page_source.lower():
                        print(f"[{email}] Likely logged in (found 'sign out').")
                        time.sleep(3)
                        if not keep_open and driver:
                            driver.quit()
                            driver = None
                        return True
                except Exception:
                    pass

                print(f"[{email}] Did not reach expected post-login URL, and no clear 'signed-in' indicator found.")
                save_page_source(driver, f"unknown_postlogin_{email}")
                if retry_count < max_retries:
                    retry_count += 1
                    if not keep_open and driver:
                        driver.quit()
                        driver = None
                    print(f"[{email}] Retrying (unknown post-login state).")
                    time.sleep(random.uniform(2, 5))
                    continue
                else:
                    print(f"[{email}] Max retries reached without clear login success. Aborting.")
                    return False

            

        except Exception as exc:
            print(f"[{email}] Exception during login attempt: {exc}")
            print(traceback.format_exc())
            try:
                if driver:
                    save_page_source(driver, f"exception_{email}")
            except Exception:
                pass
            if retry_count < max_retries:
                retry_count += 1
                if not keep_open and driver:
                    try:
                        driver.quit()
                        driver = None
                    except Exception:
                        pass
                print(f"[{email}] Retrying after exception...")
                time.sleep(random.uniform(2, 5))
                continue
            else:
                print(f"[{email}] Max retries reached after exceptions. Aborting.")
                return False


    return False 