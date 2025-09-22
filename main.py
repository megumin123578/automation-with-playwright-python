
import time
import threading
import random
from module import *


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
        time.sleep(random.uniform(5, 5.5))

    for t in threads:
        t.join()

    print("All done. Summary:")
    for e, r in results.items():
        print(f" - {e}: {'SUCCESS' if r else 'FAIL'}")

if __name__ == "__main__":
    main()
