from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import threading

# Danh sách tài khoản Google (email/số điện thoại và mật khẩu)
accounts = [
    {"email": "vuvietdu@gmail.com", "password": "Du123456"},
    {"email": "phuongtrinhthai661@gmail.com", "password": "IW3JDeiD"},
    # Thêm các tài khoản khác vào đây
]

def login_google(email, password):
    try:
        # Cấu hình Chrome options cho chế độ ẩn danh
        chrome_options = Options()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        
        # Khởi tạo trình duyệt
        driver = webdriver.Chrome(options=chrome_options)
        
        print(f"Đang đăng nhập với tài khoản: {email}")
        
        # Mở trang đăng nhập Google
        driver.get("https://accounts.google.com/signin")
        
        # Nhập email
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "identifierId"))
        )
        email_field.send_keys(email)
        driver.find_element(By.ID, "identifierNext").click()
        
        # Chờ và nhập mật khẩu
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "Passwd"))
        )
        password_field.send_keys(password)
        driver.find_element(By.ID, "passwordNext").click()
        
        # Chờ đăng nhập thành công (kiểm tra bằng URL hoặc tiêu đề trang)
        WebDriverWait(driver, 10).until(
            EC.url_contains("myaccount.google.com")
        )
        print(f"Đăng nhập thành công với tài khoản: {email}")
        
        # Giữ trình duyệt mở trong 30 giây để kiểm tra
        time.sleep(30)
        
    except Exception as e:
        print(f"Lỗi khi đăng nhập với tài khoản {email}: {str(e)}")
    
    finally:
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