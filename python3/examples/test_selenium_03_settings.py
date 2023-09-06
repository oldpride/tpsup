#!/usr/bin/env python

from pprint import pformat
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
# from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
import tpsup.env
import os

env = tpsup.env.Env()
home_dir = env.home_dir

options = Options()
options.page_load_strategy = 'normal'
options.add_argument(f"--user-data-dir={home_dir}/selenium_browser")
options.add_argument("--window-size=1260,720")
options.add_argument("--disable-gpu")
options.add_argument("--enable-javascript")
options.add_argument("disable-infobars")
options.add_argument("--disable-infobars")
options.add_argument("--disable-extensions")
options.add_argument("--disable-dev-shm-usage")
# self.browser_options.add_argument("--headless");
options.add_argument("enable-automation")
options.add_argument("--disable-browser-side-navigation")
# options.set_capability("browserVersion", "104")

# https://stackoverflow.com/questions/65080685
# disables USB: usb_device_handle_win.cc:
#     1048 Failed to read descriptor from node connection
options.add_experimental_option('excludeSwitches', ['enable-logging'])

# for file download
options.add_experimental_option(
    "prefs",
    {
        "download.default_directory": "/tmp",
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    },
)

SITEBASE = os.environ['SITEBASE']

if not env.isLinux:
    options.binary_location = f"{SITEBASE}/Windows/10.0/Chrome/Application/chrome.exe"

print(f"options.arguments = \n{pformat(options.arguments)}")

driver_args = [
    "--verbose",
]  # for chromedriver

# https://www.selenium.dev/documentation/webdriver/drivers/service/
# default is to use chromedriver on command line
# service=ChromeService(ChromeDriverManager().install()) # this is not default service.

if not env.isLinux:
    service = ChromeService(
        # he Service classes are for managing the starting and stopping of local drivers.
        executable_path=f"{SITEBASE}/Windows/10.0/chromedriver/chromedriver.exe",
        log_path=f"{home_dir}/selenium_driver.log",
        driver_args=driver_args,
    )
else:
    service = ChromeService(
        log_path=f"{home_dir}/selenium_driver.log",
        driver_args=driver_args,
    )


driver = webdriver.Chrome(
    service=service,
    options=options
)
driver.get("http://www.google.com")
print(f'Page title was {driver.title}')

# sleep 5 seconds so you can see the page load
time.sleep(3)
driver.quit()
