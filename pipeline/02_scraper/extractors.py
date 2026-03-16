import requests
from playwright.sync_api import sync_playwright
from time import sleep

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive"
}


def fetch_requests(url, retries=3):

    for i in range(retries):

        try:
            r = requests.get(url, headers=HEADERS, timeout=15)

            r.raise_for_status()

            return r.text, r.status_code

        except Exception as e:

            print("requests retry:", i + 1)

            sleep(3)

    return None, None


def fetch_browser(url):

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(headless=True)

            page = browser.new_page()

            page.goto(url, wait_until="domcontentloaded")

            html = page.content()

            browser.close()

            return html

    except Exception as e:

        print("browser fetch failed:", e)

        return None


def is_cloudflare_page(html):

    if not html:
        return False

    html_lower = html.lower()

    if "just a moment" in html_lower:
        return True

    if "wait a moment" in html_lower:
        return True

    if "checking your browser" in html_lower:
        return True

    if "cloudflare" in html_lower:
        return True

    return False


def is_html_empty(html):

    if not html:
        return True

    html_lower = html.lower()

    if len(html) < 2000:
        return True

    if "enable javascript" in html_lower:
        return True

    if "just a moment" in html_lower:
        return True

    if "checking your browser" in html_lower:
        return True

    return False