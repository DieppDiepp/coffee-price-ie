import requests
from playwright.sync_api import sync_playwright

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/"
}


def fetch_requests(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.text, r.status_code
    except Exception:
        return None, None


def fetch_browser(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto(url, wait_until="networkidle", timeout=30000)

            html = page.content()
            browser.close()

            return html
    except Exception:
        return None


def is_html_empty(html):

    if not html:
        return True

    if len(html) < 2000:
        return True

    if "enable javascript" in html.lower():
        return True

    return False