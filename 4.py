from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
import threading
from webdriver_manager.chrome import ChromeDriverManager
import traceback

# Danh sách tài khoản Google
accounts = [
    {"email": "vuvietdu2003@gmail.com", "password": "Du123456"},
]

def login_google(email, password):
    driver = None
    try:
        # Cấu hình Chrome options (anti-detection enhancements)
        chrome_options = Options()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Hide automation flag
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")  # Spoof user agent

        # Khởi tạo trình duyệt
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")  # Hide webdriver property
        
        print(f"Đang đăng nhập với tài khoản: {email}")
        
        # Mở trang đăng nhập Google
        driver.get("https://accounts.google.com/signin")
        
        # Nhập email (with wait for clickability)
        email_field = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "identifierId"))
        )
        email_field.clear()
        email_field.send_keys(email)
        driver.find_element(By.ID, "identifierNext").click()
        
        # Chờ và xử lý password field (improved wait + interaction)
        password_field = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.NAME, "Passwd"))  # Use name="Passwd" (common for Google)
        )
        
        # Scroll into view and click to focus
        driver.execute_script("arguments[0].scrollIntoView(true);", password_field)
        time.sleep(1)  # Brief pause for scroll
        ActionChains(driver).move_to_element(password_field).click().perform()
        
        # Send keys slowly (character by character to mimic human)
        for char in password:
            password_field.send_keys(char)
            time.sleep(0.1)  # Small delay per character
        
        driver.find_element(By.ID, "passwordNext").click()
        
        # Check for CAPTCHA or errors (basic handling)
        if "captcha" in driver.page_source.lower():
            print(f"CAPTCHA detected for {email}. Manual intervention needed.")
            time.sleep(30)  # Pause for manual solve
        elif "wrong" in driver.page_source.lower() or "invalid" in driver.page_source.lower():
            print(f"Invalid credentials or block for {email}.")
            return
        
        # Chờ đăng nhập thành công
        WebDriverWait(driver, 20).until(
            EC.url_contains("myaccount.google.com")
        )
        print(f"Đăng nhập thành công với tài khoản: {email}")
        
        # Giữ trình duyệt mở trong 10 giây
        time.sleep(10)
        
    except Exception as e:
        print(f"Lỗi khi đăng nhập với tài khoản {email}: {str(e)}")
        print(traceback.format_exc())
    
    finally:
        if driver:
            driver.quit()

def main():
    threads = []
    
    # Tạo luồng riêng cho mỗi tài khoản
    for account in accounts:
        thread = threading.Thread(
            target=login_google,
            args=(account["email"], account["password"])
        )
        threads.append(thread)
        thread.start()
    
    # Chờ tất cả luồng hoàn thành
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()