#!/usr/bin/env python3
"""Test Chrome/ChromeDriver setup"""

print("Testing Chrome setup...")
print("=" * 50)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os
import platform

print(f"Platform: {platform.system()}")
print(f"Python version: {platform.python_version()}")

# Setup options
chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

print("\nGetting ChromeDriver path...")
driver_path = ChromeDriverManager().install()
print(f"Raw path from ChromeDriverManager: {driver_path}")

# Fix for webdriver-manager bug on macOS ARM64
if 'THIRD_PARTY_NOTICES.chromedriver' in driver_path:
    driver_dir = os.path.dirname(driver_path)
    actual_driver = os.path.join(driver_dir, 'chromedriver')
    if os.path.exists(actual_driver):
        driver_path = actual_driver
        os.chmod(driver_path, 0o755)
        print(f"Fixed path: {driver_path}")

print(f"\nFinal driver path: {driver_path}")
print(f"Driver exists: {os.path.exists(driver_path)}")
print(f"Driver is executable: {os.access(driver_path, os.X_OK)}")

print("\nInitializing Chrome...")
try:
    driver = webdriver.Chrome(
        service=Service(driver_path),
        options=chrome_options
    )
    print("✓ Chrome initialized successfully!")

    print("\nTesting navigation...")
    driver.get("https://www.google.com")
    print(f"✓ Navigation successful! Title: {driver.title}")

    driver.quit()
    print("✓ Chrome closed successfully!")
    print("\n" + "=" * 50)
    print("✓ ALL TESTS PASSED!")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
