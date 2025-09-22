from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import threading
import random
import traceback
import re
from webdriver_manager.chrome import ChromeDriverManager

# Danh sách tài khoản Google
accounts = [
    {"email": "megumin123578@gmail.com", "password": "V!etdu1492003"},
    {"email": "phuongtrinhthai661@gmail.com", "password": "IW3JDeiD"},
]

def sanitize_filename(s: str) -> str:
    return re.sub(r"[^\w\-_\. ]", "_", s)

def save_page_source(driver, prefix: str):
    try:
        fname = f"{sanitize_filename(prefix)}_{int(time.time())}.html"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"Saved page source to {fname}")
    except Exception as e:
        print(f"Failed to save page source: {e}")

def detect_google_login_error(driver):
    try:
        possible_locators = [
            (By.XPATH, "//*[@class='o6cuMc']"),
            (By.XPATH, "//*[@aria-live='assertive']"),
            (By.XPATH, "//div[contains(@class,'RobaIf')]"),  # fallback (rare)
            (By.XPATH, "//div[contains(@class,'dEOOab')]"),  # other possible
        ]
        for by, xp in possible_locators:
            els = driver.find_elements(by, xp)
            for el in els:
                text = el.text.strip()
                if text:
                    return text
    except Exception:
        pass
    return None

def is_captcha_present(driver):
    page = driver.page_source.lower()
    return ("captcha" in page) or ("recaptcha" in page) or ("g-recaptcha" in page)

def login_google(
    email,
    password,
    max_retries=2,
    manual_captcha_wait=90,
    expected_post_login_url_contains="labs.google/flow",
    keep_open=False
):
    driver = None
    retry_count = 0

    while retry_count <= max_retries:
        try:
            # --- Chrome options / anti-detection tweaks ---
            chrome_options = Options()
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

            # Hide webdriver property from simple detection scripts
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
            time.sleep(random.uniform(0.3, 0.8))

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
                    EC.element_to_be_clickable((By.NAME, "password"))
                )
            except Exception:
                try:
                    password_field = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.NAME, "Passwd"))
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
                # ✅ KHÔNG quit nếu keep_open=True
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
        finally:
            # 🔐 Chỉ đóng trong finally nếu KHÔNG keep_open
            if not keep_open and driver:
                try:
                    driver.quit()
                    driver = None
                except Exception:
                    pass

    return False  # fallback

def main():
    threads = []
    results = {}

    def wrapper(acc):
        email = acc["email"]
        password = acc["password"]
        
        ok = login_google(email, password, max_retries=2, keep_open=True)
        results[email] = ok
        print(f"[{email}] Finished with result: {ok}")

    for account in accounts:
        t = threading.Thread(target=wrapper, args=(account,))
        threads.append(t)
        t.start()
        # Stagger để giảm rate-limit
        time.sleep(random.uniform(5, 10))

    for t in threads:
        t.join()

    print("All done. Summary:")
    for e, r in results.items():
        print(f" - {e}: {'SUCCESS' if r else 'FAIL'}")

if __name__ == "__main__":
    main()
