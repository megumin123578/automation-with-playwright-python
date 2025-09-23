import traceback
import re
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import random


DEBUG = False

def sanitize_filename(s: str) -> str:
    return re.sub(r"[^\w\-_\. ]", "_", s)

def save_page_source(driver, prefix: str):
    if not DEBUG:
        return
    try:
        fname = f"{sanitize_filename(prefix)}_{int(time.time())}.html"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"Saved page source to {fname}")
    except Exception as e:
        print(f"Failed to save page source: {e}")

def detect_google_login_error(driver):
    try:
        possible_locators = [
            (By.XPATH, "//*[@class='o6cuMc']"),
            (By.XPATH, "//*[@aria-live='assertive']"),
            (By.XPATH, "//div[contains(@class,'RobaIf')]"),  
            (By.XPATH, "//div[contains(@class,'dEOOab')]"),  
        ]
        for by, xp in possible_locators:
            els = driver.find_elements(by, xp)
            for el in els:
                text = el.text.strip()
                if text:
                    return text
    except Exception:
        pass
    return None

def is_captcha_present(driver):
    page = driver.page_source.lower()
    return ("captcha" in page) or ("recaptcha" in page) or ("g-recaptcha" in page)


