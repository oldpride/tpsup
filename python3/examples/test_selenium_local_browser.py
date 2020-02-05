#!/usr/bin/env python3

# https://chromedriver.chromium.org/getting-started


import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

headless = False

# chrome_options will be used on chrome browser's command line not chromedriver's commandline
chrome_options = Options()
if headless:
    chrome_options.add_argument("--headless")

chrome_options.add_argument('--no-sandbox')  # to be able to run without root
chrome_options.add_argument('--disable-dev_shm-usage')  # to be able to run without root
# chrome_options.add_argument('--proxy-pac-url=http://pac.abc.net')  # to run with proxy

driver = webdriver.Chrome('chromedriver', options=chrome_options)  # make sure chromedriver is in the PATH
print(f'driver.title={driver.title}')

url = 'http://www.google.com/'
driver.get(url);

if not headless:
    time.sleep(5)  # Let the user actually see something!

try:
    search_box = driver.find_element_by_name('q')
except NoSuchElementException as e:
    print(e)
else:
    search_box.send_keys('ChromeDriver')
    search_box.submit()
    if not headless:
        time.sleep(5)  # Let the user actually see something!
driver.quit()
