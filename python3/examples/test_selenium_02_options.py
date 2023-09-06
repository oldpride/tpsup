#!/usr/bin/env python

# copied from https://www.selenium.dev/documentation/webdriver/drivers/options/

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService

options = Options()
options.page_load_strategy = 'normal'
driver = webdriver.Chrome(
    service=ChromeService(ChromeDriverManager().install()),
    options=options
)
driver.get("http://www.google.com")

# sleep 5 seconds so you can see the page load
time.sleep(5)
driver.quit()
