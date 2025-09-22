

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import traceback
import time
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
        
        # Khởi tạo trình duyệt
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(60)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print(f"Đang đăng nhập với tài khoản: {email}")
        
        # Mở trang Google Flow
        driver.get("https://labs.google/flow/about")
        
        # Chờ và click nút "Create with Flow"
        create_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Create with Flow')]"))
        )
        time.sleep(1)
        ActionChains(driver).move_to_element(create_button).click().perform()
        print(f"Đã click 'Create with Flow' cho {email}")
        
        # Kiểm tra nếu có popup đăng nhập
        original_window = driver.current_window_handle
        WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))  # Chờ popup
        for window_handle in driver.window_handles:
            if window_handle != original_window:
                driver.switch_to.window(window_handle)
                break
        
        # Chờ trang đăng nhập Google xuất hiện
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
        time.sleep(2)
        if "captcha" in driver.page_source.lower() or "recaptcha" in driver.page_source.lower():
            print(f"CAPTCHA detected for {email}. Waiting for manual intervention (60 seconds).")
            print(f"Browser will remain open. Solve the CAPTCHA in the browser window.")
            time.sleep(60)
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
            EC.url_contains("myaccount.google.com")  # Hoặc URL sau đăng nhập của Flow
        )
        print(f"Đăng nhập thành công với tài khoản: {email}")
        
        # Giữ trình duyệt mở trong 10 giây
        time.sleep(10)
        
    except Exception as e:
        print(f"Lỗi khi đăng nhập với tài khoản {email}: {str(e)}")
        print(traceback.format_exc())
        # Lưu page source để debug
        if driver:
            with open(f"page_source_{email}.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                print("Browser already closed or session invalid.")