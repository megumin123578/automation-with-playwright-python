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
from webdriver_manager.chrome import ChromeDriverManager
import traceback

# Danh sách tài khoản Google
accounts = [
    {"email": "megumin123578@gmail.com", "password": "V!etdu1492003"},
    {"email": "phuongtrinhthai661@gmail.com", "password": "IW3JDeiD"},
]

def login_google(email, password, max_retries=2):
    driver = None
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            # Cấu hình Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--incognito")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
            
            # Khởi tạo trình duyệt
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(60)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print(f"Đang đăng nhập với tài khoản: {email} (Thử {retry_count + 1}/{max_retries + 1})")
            
            # Mở trang Google Flow
            driver.get("https://labs.google/flow/about")
            time.sleep(random.uniform(2, 4))  # Random delay để tránh bị chặn
            
            # Xử lý cookie banner nếu có
            try:
                cookie_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]"))
                )
                cookie_button.click()
                print("Dismissed cookie banner")
            except:
                print("No cookie banner found")
            
            # Chờ và click nút "Create with Flow"
            create_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'create with flow')]"))
            )

            ActionChains(driver).move_to_element(create_button).click().perform()
            print(f"Đã click 'Create with Flow' cho {email}")
            
            # Kiểm tra popup hoặc redirect
            original_window = driver.current_window_handle
            try:
                WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
                print(f"Popup detected. Current window handles: {driver.window_handles}")
                for window_handle in driver.window_handles:
                    if window_handle != original_window:
                        driver.switch_to.window(window_handle)
                        break
            except:
                print("No popup detected, assuming redirect in same window")
            
            # Chờ trang đăng nhập Google
            WebDriverWait(driver, 20).until(
                EC.url_contains("accounts.google.com")
            )
            print(f"Đã chuyển đến trang đăng nhập Google cho {email}")
            
            # Nhập email
            email_field = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "identifierId"))
            )
            email_field.clear()
            email_field.send_keys(email)
            time.sleep(random.uniform(0.5, 1.0))
            driver.find_element(By.ID, "identifierNext").click()
            
            # Chờ và xử lý password field
            password_field = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.NAME, "Passwd"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", password_field)
            time.sleep(random.uniform(0.5, 1.5))
            ActionChains(driver).move_to_element(password_field).click().perform()
            
            # Send password slowly
            for char in password:
                password_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            driver.find_element(By.ID, "passwordNext").click()
            
            # Check for CAPTCHA or errors
            time.sleep(random.uniform(2, 4))
            if "captcha" in driver.page_source.lower() or "recaptcha" in driver.page_source.lower():
                print(f"CAPTCHA detected for {email}. Waiting for manual intervention (90 seconds).")
                print(f"Browser will remain open. Solve the CAPTCHA in the browser window.")
                time.sleep(90)  # Extended pause
                try:
                    driver.find_element(By.ID, "passwordNext").click()
                except:
                    print("Could not click Next after CAPTCHA. Check if CAPTCHA was solved correctly.")
            
            # Check for login errors
            time.sleep(1)  # Đợi để page source cập nhật
            page_source = driver.page_source.lower()
            if "wrong" in page_source or "invalid" in page_source:
                print(f"Invalid credentials or block for {email}. Saving page source for debugging.")
                with open(f"page_source_error_{email}.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                if retry_count < max_retries:
                    print("Retrying login...")
                    retry_count += 1
                    driver.quit()
                    continue
                else:
                    print(f"Max retries reached for {email}. Aborting.")
                    return
            
            # Check for 2FA or additional verification
            if "verify" in page_source or "2-step" in page_source or "phone" in page_source:
                print(f"2FA or additional verification required for {email}. Saving page source for debugging.")
                with open(f"page_source_2fa_{email}.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("Script cannot handle 2FA automatically. Please disable 2FA or complete manually.")
                return
            
            # Chờ đăng nhập thành công
            WebDriverWait(driver, 30).until(
                EC.url_contains("labs.google/flow")  # Adjust based on actual redirect
            )
            print(f"Đăng nhập thành công với tài khoản: {email}")
            
            # Giữ trình duyệt mở trong 10 giây
            time.sleep(10)
            break  # Thoát vòng lặp retry nếu thành công
            
        except Exception as e:
            print(f"Lỗi khi đăng nhập với tài khoản {email}: {str(e)}")
            print(traceback.format_exc())
            if driver:
                with open(f"page_source_error_{email}.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
            if retry_count < max_retries:
                print("Retrying login...")
                retry_count += 1
                if driver:
                    driver.quit()
                continue
            else:
                print(f"Max retries reached for {email}. Aborting.")
                return
        
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    print("Browser already closed or session invalid.")
    
def main():
    threads = []
    
    for account in accounts:
        thread = threading.Thread(
            target=login_google,
            args=(account["email"], account["password"])
        )
        threads.append(thread)
        thread.start()
        time.sleep(random.uniform(5, 10))  # Random delay to avoid rate limits
        
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()