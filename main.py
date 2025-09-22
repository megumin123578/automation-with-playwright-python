
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

# ====== CẤU HÌNH ======
BASE_PROFILE_DIR = Path.cwd() / "pw_profiles"   # nơi lưu persistent contexts
BASE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

PROFILES: List[Dict[str, Any]] = [
    {"name": "acc1", "username": "vuvietdu2003@gmail.com", "password": "Du123456", "proxy": None},
    {"name": "acc2", "username": "phuongtrinhthai661@gmail.com", "password": "IW3JDeiD", "proxy": None},
]

LOGIN_URL = "https://aistudio.google.com/models/veo-3"  
DASHBOARD_URL_KEYWORD = "dashboard"      # hoặc đặt CSS để nhận biết đã login xong
HEADLESS = False                          # để True nếu muốn ẩn
CONCURRENCY = 4                           # số profile chạy song song tối đa


def make_proxy(proxy: Optional[str]) -> Optional[Dict[str, str]]:
    if not proxy:
        return None
    return {"server": proxy}


async def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


async def login_flow(pw, profile_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mỗi profile = 1 persistent context (user_data_dir) => giữ cookie/session dài hạn.
    Lần đầu chạy sẽ login bằng username/password; những lần sau có thể bỏ qua vì session còn.
    """
    name = profile_cfg["name"]
    username = profile_cfg.get("username")
    password = profile_cfg.get("password")
    proxy = profile_cfg.get("proxy")

    user_data_dir = BASE_PROFILE_DIR / name
    await ensure_dir(user_data_dir)

    chromium = pw.chromium

    context = await chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        headless=HEADLESS,
        proxy=make_proxy(proxy),
        args=[
            # Các flags hữu ích
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ],
        viewport={"width": 1280, "height": 800},
    )

    page = await context.new_page()

    try:

        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)

        if DASHBOARD_URL_KEYWORD in page.url:
            await context.close()
            return {"name": name, "ok": True, "msg": "Already logged in (session reused)"}
        
        await page.fill("input[name='username']", username, timeout=20_000)
        await page.fill("input[name='password']", password, timeout=20_000)
        await page.click("button:has-text('Login')", timeout=20_000)

        try:
            await page.wait_for_timeout(1000)
            for _ in range(30):  # 30 * 500ms = 15s
                if DASHBOARD_URL_KEYWORD in page.url:
                    break
                await page.wait_for_timeout(500)
        except PWTimeoutError:
            pass

        if DASHBOARD_URL_KEYWORD in page.url:
            # Đã login — cookie được lưu trong user_data_dir => lần sau mở lại khỏi nhập
            result = {"name": name, "ok": True, "msg": "Logged in"}
        else:
            result = {"name": name, "ok": False, "msg": f"Maybe failed, current_url={page.url}"}

    except Exception as e:
        result = {"name": name, "ok": False, "msg": str(e)}
    finally:
        # Đóng context để session/LocalStorage được flush về ổ
        await context.close()

    return result


async def worker(pw, profile_cfgs: List[Dict[str, Any]]):
    tasks = [login_flow(pw, cfg) for cfg in profile_cfgs]
    return await asyncio.gather(*tasks, return_exceptions=False)


async def run_all():
    # Điều tiết concurrency nếu số profile lớn
    buckets = []
    cur = []
    for cfg in PROFILES:
        cur.append(cfg)
        if len(cur) >= CONCURRENCY:
            buckets.append(cur)
            cur = []
    if cur:
        buckets.append(cur)

    all_results = []
    async with async_playwright() as pw:
        for batch in buckets:
            batch_results = await worker(pw, batch)
            for r in batch_results:
                print(r)
            all_results.extend(batch_results)
    return all_results


if __name__ == "__main__":
    asyncio.run(run_all())
