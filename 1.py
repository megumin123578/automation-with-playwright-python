# auto_login_google_live.py
import asyncio, time
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

LOGIN_URL = "https://aistudio.google.com/models/veo-3"  # trang bạn muốn vào trước
GET_STARTED_SELECTOR = "text=Get started, text=Bắt đầu"  # sửa nếu nút khác chữ
HEADLESS = False
NAV_TIMEOUT = 30_000
CONCURRENCY = 4
PAUSE_ON_2FA = True  # nếu gặp 2FA/CAPTCHA thì pause 


PROFILES: List[Dict[str, Any]] = [
    {"name": "acc1", "email": "vuvietdu2003@gmail.com", "password": "Du123456"},
    {"name": "acc2", "email": "phuongtrinhthai661@gmail.com", "password": "IW3JDeiD"},

]

async def click_if_exists(page, selector: str, timeout_ms=5000):
    try:
        await page.click(selector, timeout=timeout_ms)
        return True
    except Exception:
        return False

async def find_google_page(context) -> Optional[Any]:
    for _ in range(40):  # ~20s
        for pg in context.pages:
            if "accounts.google.com" in pg.url:
                return pg
        await asyncio.sleep(0.5)
    return None

async def fill_google_login(google_page, email: str, password: str):
    # Điền email
    await google_page.wait_for_selector("input[type='email']", timeout=15_000)
    await google_page.fill("input[type='email']", email)
    await google_page.click("#identifierNext")
    # Điền password
    await google_page.wait_for_selector("input[type='password']", timeout=15_000)
    await google_page.fill("input[type='password']", password)
    await google_page.click("#passwordNext")

async def login_one(pw, cfg: Dict[str, Any]) -> Dict[str, Any]:
    name, email, password = cfg["name"], cfg["email"], cfg["password"]
    # 1 browser riêng cho isolation ổn định hơn
    browser = await pw.chromium.launch(headless=HEADLESS, args=["--disable-dev-shm-usage", "--no-sandbox"])
    context = await browser.new_context(viewport={"width": 1280, "height": 800})
    page = await context.new_page()

    try:
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)

        # Click Get started (nếu có)
        await click_if_exists(page, GET_STARTED_SELECTOR, timeout_ms=7000)

        # Có trang dùng "Continue with Google"
        await click_if_exists(page, "text=Continue with Google", timeout_ms=5000)
        await click_if_exists(page, "text=Sign in with Google", timeout_ms=5000)
        await click_if_exists(page, "button[aria-label*='Sign in with Google']", timeout_ms=5000)

        # Tìm tab/redirect Google
        google_page = await find_google_page(context)
        if not google_page:
            # Có thể login inline trong cùng tab:
            if "accounts.google.com" in page.url:
                google_page = page
            else:
                # Thử nhấn lại nút google (site khác nhau có nhiều biến thể)
                await click_if_exists(page, "text=Google", timeout_ms=3000)
                google_page = await find_google_page(context)

        if not google_page:
            return {"name": name, "ok": False, "msg": "Không tìm thấy trang Google login (accounts.google.com)"}

        # Điền tài khoản
        try:
            await fill_google_login(google_page, email, password)
        except Exception as e:
            # Nếu Google yêu cầu xác minh (2FA/CAPTCHA), cho bạn can thiệp tay
            if PAUSE_ON_2FA and not HEADLESS:
                print(f"[{name}] Cần thao tác tay trên Google (2FA/CAPTCHA?): mở inspector...")
                await google_page.pause()
            else:
                return {"name": name, "ok": False, "msg": f"Lỗi khi điền Google form: {e}"}

        # Chờ quay về trang đích (aistudio…) hoặc trạng thái stable
        for _ in range(60):  # ~30s
            # kiểm tra các tab
            current_back = any("aistudio.google.com" in pg.url for pg in context.pages)
            if current_back:
                break
            await asyncio.sleep(0.5)

        # chọn tab chính (trở về site)
        main = None
        for pg in context.pages:
            if "aistudio.google.com" in pg.url:
                main = pg
                break
        if not main:
            main = page

        # kiểm tra url “đã vào”
        if "aistudio.google.com" in main.url:
            return {"name": name, "ok": True, "msg": f"Đăng nhập xong, url={main.url}"}
        else:
            return {"name": name, "ok": False, "msg": f"Chưa xác nhận được login, url={main.url}"}

    except Exception as e:
        return {"name": name, "ok": False, "msg": str(e)}
    finally:
        await context.close()
        await browser.close()

async def run_all():
    results = []
    sem = asyncio.Semaphore(CONCURRENCY)
    async with async_playwright() as pw:
        async def task(cfg):
            async with sem:
                print(f"[{cfg['name']}] start")
                r = await login_one(pw, cfg)
                print(f"[{cfg['name']}] -> {r}")
                return r
        tasks = [task(c) for c in PROFILES]
        for fut in asyncio.as_completed(tasks):
            results.append(await fut)
    return results

if __name__ == "__main__":
    asyncio.run(run_all())
