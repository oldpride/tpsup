#!/usr/bin/env python

from pprint import pformat
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
import tpsup.env
import os


env = tpsup.env.Env()
home_dir = env.home_dir


# # https://www.selenium.dev/documentation/webdriver/troubleshooting/logging/
# import logging
# logger = logging.getLogger('selenium')
# logger.setLevel(logging.DEBUG)  # default is WARN. DEBUG is the most verbose.

options = Options()
options.page_load_strategy = 'normal'
options.add_argument(f"--user-data-dir={home_dir}/selenium_browser")
options.add_argument("--window-size=1260,720")
options.add_argument("--disable-gpu")
options.add_argument("--enable-javascript")
options.add_argument("--disable-infobars")
options.add_argument("--disable-extensions")
options.add_argument("--disable-dev-shm-usage")
# self.browser_options.add_argument("--headless");
options.add_argument("--enable-automation")
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

if env.isLinux:
    options.add_argument(
        "--no-sandbox")  # allow to run without root
    options.add_argument(
        "--disable-dev_shm-usage")  # allow to run without root
    # options.binary_location = f"/google/chrome/google-chrome"
    options.binary_location = f"/opt/google/chrome/google-chrome"
else:
    options.binary_location = f"{SITEBASE}/Windows/10.0/Chrome/Application/chrome.exe"

print(f"options.arguments = \n{pformat(options.arguments)}")
print()
print(f"options.to_capabilities = \n {pformat(options.to_capabilities())}")
print()
print('browser command =')
print(f"{options.binary_location} {' '.join(options.arguments)}")

driver_args = [
    "--verbose",
    "--enable-chrome-logs",
    f"--log-path={home_dir}/selenium_driver2.log",

]  # for chromedriver

# https://www.selenium.dev/documentation/webdriver/drivers/service/
# default is to use chromedriver on command line
# service=ChromeService(ChromeDriverManager().install()) # this is not default service.

# The Service classes are for managing the starting and stopping of local drivers.
if env.isLinux:
    service = ChromeService(
        executable_path=f"/usr/bin/chromedriver",
        service_args=driver_args,

        # log_path will be deprecated in the future, use log_output instead
        # see <venv>\Lib\site-packages\selenium\webdriver\chromium\service.py
        # log_path=f"{home_dir}/selenium_driver.log",
        # I set it in service_args instead. see above
    )
else:
    service = ChromeService(
        executable_path=f"{SITEBASE}/Windows/10.0/chromedriver/chromedriver.exe",
        service_args=driver_args,
        # log_path=f"{home_dir}/selenium_driver.log", # commented out because see above
    )

# print(
#     f"\nservice.command_line_args() = {pformat(service.command_line_args())}\n")
print()
print(f"driver_command = ")
print(f"{service.path} {' '.join(service.command_line_args())}")
print()

driver = webdriver.Chrome(
    service=service,
    options=options,
)
# driver = webdriver.Chrome()

url = f"file:///{os.path.normpath(os.environ.get('TPSUP'))}/scripts/tpslnm_test_input.html"
# driver.get("http://www.google.com")
driver.get(url)

print(f'Page title was {driver.title}')

# sleep 5 seconds so you can see the page load
time.sleep(2)
driver.quit()
