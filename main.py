
from module import *
import os, json, threading, time
from collections import deque
from dataclasses import dataclass, asdict
from typing import List, Optional

# ==== config ====
ACCOUNTS_FILE = "accounts.json"
DEFAULT_CREDITS = 50
CONCURRENCY = 2              # chạy song song 2 email
SLEEP_BETWEEN_RUNS = 0.5     # nghỉ giữa các lần chạy 1 account (giảm tải)
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
        email = item.get("email")
        pwd = item.get("password")
        if not email or not pwd:
            continue
        if email in seen:
            continue
        seen.add(email)
        credits = int(item.get("credits", DEFAULT_CREDITS))
        accs.append(Account(email=email, password=pwd, credits=credits))
    return accs

def save_accounts(path: str, accounts: List[Account]) -> None:
    data = [asdict(a) for a in accounts]
    _atomic_write_json(path, data)

class Scheduler:
    def __init__(self, accounts_path: str, concurrency: int = 2):
        assert concurrency == 2, "Chế độ theo cặp yêu cầu CONCURRENCY = 2"
        self.accounts_path = accounts_path
        self.accounts: List[Account] = load_accounts(accounts_path)
        self.waiting = deque([a for a in self.accounts if a.credits > 0])

        self.lock = threading.Lock()
        self.cv = threading.Condition(self.lock)
        self.stop_event = threading.Event()

        # Trạng thái cặp hiện tại: đúng 2 slot
        self.current_pair: List[Optional[Account]] = [None, None]
        self.finished = [False, False]  # slot 0, slot 1 đã xong cặp hiện tại?

    # ---- persist helpers ----
    def persist(self):
        with self.lock:
            save_accounts(self.accounts_path, self.accounts)

    def decrement_and_save(self, acc: Account, n: int = 1):
        with self.lock:
            acc.credits = max(0, acc.credits - n)
            save_accounts(self.accounts_path, self.accounts)

    # ---- pair coordination ----
    def _pop_next_account(self) -> Optional[Account]:
        while self.waiting:
            a = self.waiting.popleft()
            if a.credits > 0:
                return a
        return None

    def _fill_next_pair(self):
        """Gọi khi BẮT ĐẦU hoặc khi cả hai slot xong cặp hiện tại: nạp cặp kế tiếp."""
        self.current_pair[0] = self._pop_next_account()
        self.current_pair[1] = self._pop_next_account()
        self.finished = [False, False]

    def _ensure_pair_started(self) -> bool:
        """Khởi tạo cặp đầu tiên nếu chưa có. Trả về False nếu hết hàng đợi."""
        if self.current_pair[0] is None and self.current_pair[1] is None:
            self._fill_next_pair()
        # Nếu vẫn None None => hết hàng đợi
        return not (self.current_pair[0] is None and self.current_pair[1] is None)

    # ---- worker ----
    def worker(self, slot_id: int):
        idx = slot_id - 1  # slot 1 -> 0, slot 2 -> 1
        name = f"PROGRAM-{slot_id}"

        while not self.stop_event.is_set():
            with self.cv:
                # Bắt đầu hoặc chờ cặp hiện tại sẵn sàng
                if not self._ensure_pair_started():
                    print(f"[{name}] Hết hàng đợi. Kết thúc.")
                    return

                acc = self.current_pair[idx]
                if acc is None:
                    # Cặp lẻ (chỉ còn 1 account cho slot kia) -> slot này nghỉ
                    print(f"[{name}] Không có account cho slot này trong cặp hiện tại. Chờ...")
                    # Chờ đến khi cặp mới được nạp
                    while not self.stop_event.is_set():
                        self.cv.wait(timeout=0.5)
                        if self.current_pair[idx] is not acc:
                            break
                    continue

            # Ở ngoài lock: chạy account của slot mình cho đến khi hết credits
            print(f"[{name}] Bắt đầu với {acc.email} (credits={acc.credits})")

            # (TUỲ CHỌN) nếu bạn có make_driver để giữ 1 Chrome tới khi credit=0:
            driver = None
            try:
                try:
                    driver = make_driver()  # nếu không có, bỏ 2 dòng này đi
                except Exception:
                    driver = None

                while acc.credits > 0 and not self.stop_event.is_set():
                    try:
                        ok = login_google(
                            acc.email,
                            acc.password,
                            max_retries=2,
                            manual_captcha_wait=90,
                            expected_post_login_url_contains=EXPECTED_URL_SUBSTR,
                            keep_open=(driver is not None),
                            driver=driver
                        )
                        self.decrement_and_save(acc, 1)
                        left = acc.credits
                        print(f"[{name}] {acc.email} done 1 credit -> còn {left}")
                        if left > 0:
                            time.sleep(SLEEP_BETWEEN_RUNS)
                    except KeyboardInterrupt:
                        self.stop_event.set()
                        print(f"[{name}] Nhận Ctrl+C. Đang dừng...")
                        return
                    except Exception as e:
                        print(f"[{name}] Lỗi khi chạy {acc.email}: {e}")
                        self.decrement_and_save(acc, 1)
                        if acc.credits > 0:
                            time.sleep(SLEEP_BETWEEN_RUNS)
            finally:
                # CHỈ đóng khi kết thúc account của cặp hiện tại
                if driver is not None:
                    try:
                        driver.quit()
                        print(f"[{name}] Đã đóng Chrome cho {acc.email} (credits=0).")
                    except Exception:
                        pass

            # Báo đã xong slot này và CHỜ slot kia cũng xong rồi mới nạp cặp mới
            with self.cv:
                self.finished[idx] = True
                # Nếu cả hai slot đã xong cặp hiện tại -> nạp cặp kế tiếp
                if all(self.finished[i] or self.current_pair[i] is None for i in (0, 1)):
                    print(f"[PAIR] Cả hai slot đã xong cặp: "
                          f"{self.current_pair[0].email if self.current_pair[0] else 'None'} & "
                          f"{self.current_pair[1].email if self.current_pair[1] else 'None'} -> nạp cặp mới")
                    self._fill_next_pair()
                    self.cv.notify_all()
                else:
                    # Slot này xong sớm -> CHỜ đến khi slot kia xong để cùng chuyển cặp
                    while not self.stop_event.is_set() and not all(
                        self.finished[i] or self.current_pair[i] is None for i in (0, 1)
                    ):
                        self.cv.wait(timeout=0.5)
                    # cặp đã chuyển, vòng while lớn tiếp tục và lấy acc mới

        print(f"[{name}] stop_event bật, dừng.")

    # ---- run ----
    def run(self):
        with self.cv:
            if not self._ensure_pair_started():
                print("Không có tài khoản nào còn credits > 0.")
                return

        threads = []
        for i in range(2):  # đúng 2 slot
            t = threading.Thread(target=self.worker, args=(i+1,), daemon=True)
            t.start()
            threads.append(t)

        try:
            for t in threads:
                while t.is_alive():
                    t.join(timeout=0.5)
        except KeyboardInterrupt:
            print("Nhận Ctrl+C. Đang dừng tất cả...")
            self.stop_event.set()
            for t in threads:
                t.join(timeout=5)
        finally:
            self.persist()
            print("Đã lưu trạng thái credits và thoát.")


if __name__ == "__main__":
    sch = Scheduler(ACCOUNTS_FILE, concurrency=CONCURRENCY)
    sch.run()
