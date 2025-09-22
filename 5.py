from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import threading
from webdriver_manager.chrome import ChromeDriverManager
import traceback

# Danh sách tài khoản Google
accounts = [
    {"email": "megumin123578@gmail.com", "password": "V!etdu1492003"},
    {"email": "phuongtrinhthai661@gmail.com", "password": "IW3JDeiD"},
]

def login_google(email, password):
    driver = None
    try:
        # Cấu hình Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
        # Removed --disable-gpu; add --enable-unsafe-swiftshader if needed
        # chrome_options.add_argument("--enable-unsafe-swiftshader")

        # Khởi tạo trình duyệt
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(60)  # Increase timeout
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print(f"Đang đăng nhập với tài khoản: {email}")
        
        # Mở trang đăng nhập Google
        driver.get("https://accounts.google.com/signin")
        
        # Nhập email
        email_field = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "identifierId"))
        )
        email_field.clear()
        email_field.send_keys(email)
        driver.find_element(By.ID, "identifierNext").click()
        
        # Chờ và xử lý password field
        password_field = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.NAME, "Passwd"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", password_field)
        time.sleep(1)
        ActionChains(driver).move_to_element(password_field).click().perform()
        
        # Send password slowly
        for char in password:
            password_field.send_keys(char)
            time.sleep(0.1)
        
        driver.find_element(By.ID, "passwordNext").click()
        
        # Check for CAPTCHA or errors
        time.sleep(2)  # Brief pause to allow page to settle
        if "captcha" in driver.page_source.lower() or "recaptcha" in driver.page_source.lower():
            print(f"CAPTCHA detected for {email}. Waiting for manual intervention (60 seconds).")
            print(f"Browser will remain open. Solve the CAPTCHA in the browser window.")
            time.sleep(60)  # Extended pause for manual CAPTCHA solving
            # After CAPTCHA, try clicking Next again
            try:
                driver.find_element(By.ID, "passwordNext").click()
            except:
                print("Could not click Next after CAPTCHA. Check if CAPTCHA was solved correctly.")
        
        # Check for login errors
        if "wrong" in driver.page_source.lower() or "invalid" in driver.page_source.lower():
            print(f"Invalid credentials or block for {email}. Aborting.")
            return
        
        # Chờ đăng nhập thành công
        WebDriverWait(driver, 30).until(
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
            try:
                driver.quit()
            except:
                print("Browser already closed or session invalid.")

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