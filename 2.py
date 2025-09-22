# auto_login_google_live_fixed.py
import asyncio, re
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError, Page

LOGIN_URL = "https://aistudio.google.com/models/veo-3"
HEADLESS = False
NAV_TIMEOUT = 30_000
CONCURRENCY = 4
PAUSE_ON_2FA = True  # nếu gặp 2FA/CAPTCHA thì pause để bạn xử lý tay

PROFILES: List[Dict[str, Any]] = [
    {"name": "acc1", "email": "vuvietdu2003@gmail.com", "password": "Du123456"},
    {"name": "acc2", "email": "phuongtrinhthai661@gmail.com", "password": "IW3JDeiD"},
    # thêm acc3, acc4 nếu cần
]

# ---------- Helpers ----------
async def accept_cookies_if_any(page: Page):
    """Đóng cookie/consent banner phổ biến nếu có (best-effort)."""
    selectors = [
        "button:has-text('Accept all')",
        "button:has-text('I agree')",
        "button:has-text('Allow all')",
        "text=Accept all",
        "text=Tôi đồng ý",
        "text=Chấp nhận tất cả",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.is_visible():
                await loc.click(timeout=2000)
                break
        except Exception:
            pass

async def click_get_started(page: Page) -> bool:
    """Cố gắng click nút 'Get started' / 'Bắt đầu' với nhiều chiến lược."""
    await accept_cookies_if_any(page)
    candidates = [
        page.get_by_role("button", name=re.compile(r"get\s*started", re.I)),
        page.get_by_role("link",   name=re.compile(r"get\s*started", re.I)),
        page.get_by_role("button", name=re.compile(r"bắt\s*đầu", re.I)),
        page.get_by_role("link",   name=re.compile(r"bắt\s*đầu", re.I)),
        page.locator("button:has-text('Get started')"),
        page.locator("a:has-text('Get started')"),
        page.locator("button:has-text('Bắt đầu')"),
        page.locator("a:has-text('Bắt đầu')"),
        page.locator("text=Get started"),
        page.locator("text=Bắt đầu"),
        # đôi khi dùng 'Try now'/'Try it'
        page.get_by_role("button", name=re.compile(r"try\s*(now|it)?", re.I)),
        page.get_by_role("link",   name=re.compile(r"try\s*(now|it)?", re.I)),
    ]
    for loc in candidates:
        try:
            await loc.first.wait_for(state="visible", timeout=4000)
            await loc.first.scroll_into_view_if_needed()
            await loc.first.click()
            return True
        except Exception:
            # thử force click nếu bị overlay
            try:
                await loc.first.scroll_into_view_if_needed()
                await loc.first.click(force=True, timeout=1500)
                return True
            except Exception:
                pass
    # thử trong iframe (nếu nút nằm bên trong)
    try:
        for f in page.frames:
            loc = f.get_by_role("button", name=re.compile(r"get\s*started", re.I))
            try:
                await loc.first.wait_for(state="visible", timeout=2000)
                await loc.first.click()
                return True
            except Exception:
                pass
    except Exception:
        pass
    return False

async def click_if_exists(page: Page, selector: str, timeout_ms=3000) -> bool:
    try:
        loc = page.locator(selector).first
        await loc.wait_for(state="visible", timeout=timeout_ms)
        await loc.scroll_into_view_if_needed()
        await loc.click()
        return True
    except Exception:
        return False

async def wait_google_page(context) -> Optional[Page]:
    """Đợi xuất hiện tab Google OAuth hoặc URL hiện tại chuyển thành accounts.google.com."""
    # nếu đã có sẵn
    for pg in context.pages:
        if "accounts.google.com" in pg.url:
            return pg
    # chờ popup mới
    try:
        new_pg = await context.wait_for_event("page", timeout=10_000)
        # popup có thể mở vào trang trung gian rồi mới chuyển accounts.google.com
        for _ in range(30):
            if "accounts.google.com" in new_pg.url:
                return new_pg
            await asyncio.sleep(0.3)
        # nếu không phải, fallback quét tất cả
        for pg in context.pages:
            if "accounts.google.com" in pg.url:
                return pg
    except Exception:
        pass
    # lần cuối: quét lại
    for pg in context.pages:
        if "accounts.google.com" in pg.url:
            return pg
    return None

async def fill_google_login(google_page: Page, email: str, password: str):
    """Xử lý 3 tình huống: chọn account, nhập email -> next, nhập password -> next."""
    # 1) “Choose an account” screen?
    try:
        # nút theo email
        acc_btn = google_page.get_by_role("button", name=re.compile(re.escape(email), re.I))
        if await acc_btn.count() > 0:
            await acc_btn.first.click()
    except Exception:
        pass

    # 2) Nếu chưa có email field thì chờ nó (inline hoặc sau khi click acc)
    try:
        await google_page.wait_for_selector("input[type='email']", timeout=8000)
        await google_page.fill("input[type='email']", email)
        await google_page.click("#identifierNext")
    except Exception:
        # có thể đã qua bước email rồi (do chọn account)
        pass

    # 3) Password
    await google_page.wait_for_selector("input[type='password']", timeout=15_000)
    await google_page.fill("input[type='password']", password)
    await google_page.click("#passwordNext")

# ---------- Main worker ----------
async def login_one(pw, cfg: Dict[str, Any]) -> Dict[str, Any]:
    name, email, password = cfg["name"], cfg["email"], cfg["password"]
    browser = await pw.chromium.launch(
        headless=HEADLESS,
        args=["--disable-dev-shm-usage", "--no-sandbox"],
    )
    context = await browser.new_context(viewport={"width": 1340, "height": 900})
    page = await context.new_page()

    try:
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)

        # click Get started / Try now / Sign in...
        clicked = await click_get_started(page)
        if not clicked:
            # fallback vài lựa chọn phổ biến
            for sel in [
                "text=Sign in",
                "text=Đăng nhập",
                "text=Continue with Google",
                "text=Sign in with Google",
                "button[aria-label*='Sign in with Google']",
                "role=button[name='Continue with Google']",
            ]:
                if await click_if_exists(page, sel, timeout_ms=4000):
                    break

        # đợi tab/redirect Google OAuth
        google_page = await wait_google_page(context)
        if not google_page:
            # có thể OAuth inline ngay trên page hiện tại
            if "accounts.google.com" in page.url:
                google_page = page
            else:
                # thử bấm lại các nút ‘Sign in with Google’
                for sel in [
                    "text=Continue with Google",
                    "text=Sign in with Google",
                    "button[aria-label*='Sign in with Google']",
                    "text=Google",
                ]:
                    if await click_if_exists(page, sel, timeout_ms=3000):
                        google_page = await wait_google_page(context)
                        if google_page:
                            break

        if not google_page:
            return {"name": name, "ok": False, "msg": "Không tìm thấy trang Google login (accounts.google.com)"}

        # điền tài khoản Google
        try:
            await fill_google_login(google_page, email, password)
        except Exception as e:
            if PAUSE_ON_2FA and not HEADLESS:
                print(f"[{name}] Cần thao tác tay (2FA/CAPTCHA/‘This browser is not secure’). Mở inspector…")
                await google_page.pause()
            else:
                return {"name": name, "ok": False, "msg": f"Lỗi khi điền Google form: {e}"}

        # chờ quay về aistudio
        for _ in range(60):   # ~30s
            if any("aistudio.google.com" in pg.url for pg in context.pages):
                break
            await asyncio.sleep(0.5)

        # chọn tab chính
        main = None
        for pg in context.pages:
            if "aistudio.google.com" in pg.url:
                main = pg
                break
        if not main:
            main = page

        # xác nhận
        if "aistudio.google.com" in main.url:
            return {"name": name, "ok": True, "msg": f"Đăng nhập xong, url={main.url}"}
        else:
            return {"name": name, "ok": False, "msg": f"Chưa xác nhận được login, url={main.url}"}

    except Exception as e:
        return {"name": name, "ok": False, "msg": str(e)}
    finally:
        await context.close()
        await browser.close()

# ---------- Runner ----------
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
