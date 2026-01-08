import os
import sys
import django
from playwright.sync_api import sync_playwright

def verify_playwright():
    print("Testing Playwright...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content("<h1>Playwright is working!</h1>")
            screenshot = page.screenshot()
            print(f"Success! Screenshot captured ({len(screenshot)} bytes).")
            browser.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_playwright()
