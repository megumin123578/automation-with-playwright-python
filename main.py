from module import *  # cần có login_google(...)
import os, json, time
from collections import deque
from dataclasses import dataclass, asdict
from typing import List

# ==== config ====
ACCOUNTS_FILE = "accounts.json"
DEFAULT_CREDITS = 50
SLEEP_BETWEEN_RUNS = 0.5
EXPECTED_URL_SUBSTR = "labs.google/flow"  # truyền vào login_google

@dataclass
class Account:
    email: str
    password: str
    credits: int = DEFAULT_CREDITS

def _atomic_write_json(path: str, data) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def load_accounts(path: str) -> List[Account]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Không thấy {path}. Hãy tạo {path} theo ví dụ.")
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    accs: List[Account] = []
    seen = set()
    for item in raw:
        email = (item.get("email") or "").strip()
        pwd = (item.get("password") or "").strip()
        if not email or not pwd:
            continue
        if email in seen:
            continue
        seen.add(email)
        try:
            credits = int(item.get("credits", DEFAULT_CREDITS))
        except Exception:
            credits = DEFAULT_CREDITS
        accs.append(Account(email=email, password=pwd, credits=credits))
    if not accs:
        raise ValueError("accounts.json rỗng hoặc không hợp lệ.")
    return accs

def save_accounts(path: str, accounts: List[Account]) -> None:
    data = [asdict(a) for a in accounts]
    _atomic_write_json(path, data)

class Scheduler:
    def __init__(self, accounts_path: str):
        self.accounts_path = accounts_path
        self.accounts: List[Account] = load_accounts(accounts_path)
        # hàng đợi tuần tự theo thứ tự file
        self.queue = deque([a for a in self.accounts if a.credits > 0])
        self._stop = False

    def persist(self):
        save_accounts(self.accounts_path, self.accounts)

    def decrement_and_save(self, acc: Account, n: int = 1):
        acc.credits = max(0, acc.credits - n)
        save_accounts(self.accounts_path, self.accounts)

    def run_one_account(self, acc: Account):
        print(f"[RUN] Bắt đầu {acc.email} (credits={acc.credits})")
        while not self._stop and acc.credits > 0:
            try:
                ok = login_google(
                    acc.email,
                    acc.password,
                    max_retries=2,
                    manual_captcha_wait=90,
                    expected_post_login_url_contains=EXPECTED_URL_SUBSTR,
                    keep_open=False  # luôn đóng Chrome sau mỗi lần -> chỉ 1 trình duyệt tồn tại
                )
                # theo yêu cầu: mỗi lần chạy -1 credit, bất kể kết quả
                self.decrement_and_save(acc, 1)
                left = acc.credits
                print(f"[RUN] {acc.email} done 1 credit (ok={ok}) -> còn {left}")
                if left > 0:
                    time.sleep(SLEEP_BETWEEN_RUNS)
            except KeyboardInterrupt:
                self._stop = True
                print("[RUN] Nhận Ctrl+C. Dừng…")
                break
            except Exception as e:
                # vẫn -1 credit theo yêu cầu
                print(f"[RUN] Lỗi {acc.email}: {e}")
                self.decrement_and_save(acc, 1)
                if acc.credits > 0:
                    time.sleep(SLEEP_BETWEEN_RUNS)
        print(f"[RUN] {acc.email} đã hết credits.")

    def run(self):
        if not self.queue:
            print("Không có tài khoản nào còn credits > 0.")
            return
        try:
            while not self._stop and self.queue:
                acc = self.queue.popleft()
                if acc.credits <= 0:
                    continue
                self.run_one_account(acc)
        except KeyboardInterrupt:
            self._stop = True
            print("Nhận Ctrl+C. Dừng…")
        finally:
            self.persist()
            print("Đã lưu trạng thái credits và thoát.")

if __name__ == "__main__":
    sch = Scheduler(ACCOUNTS_FILE)
    sch.run()
