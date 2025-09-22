
import time
import threading


from module import *


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
        time.sleep(5)  # Delay giữa các luồng để giảm rate limit
        
    # Chờ tất cả luồng hoàn thành
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()