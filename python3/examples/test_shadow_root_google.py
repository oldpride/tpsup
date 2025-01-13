#!/usr/bin/env python
from shutil import which
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchShadowRootException

chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument('disable-notifications')
chrome_options.add_argument("window-size=1280,720")
chrome_options.binary_location = which("chrome")
driver = webdriver.Chrome(options=chrome_options)
url = 'chrome-search://local-ntp/local-ntp.html'
driver.get(url)

all_elements = driver.find_elements(By.XPATH, '//*')
for el in all_elements:
    root_driver:webdriver = None
    try:
        if el.shadow_root:
            print('found shadow root in', el.get_attribute('outerHTML'))
            root_driver = el.shadow_root
    except NoSuchShadowRootException:
        continue

    # root_element:WebElement = root_driver.find_element(By.XPATH, '//*') # not working
    # error: invalid locator

    # root_element: WebElement = root_driver.find_element(By.CSS_SELECTOR, ':host')  # not working
    # root_element: WebElement = root_driver.find_element(By.CSS_SELECTOR, ':root')  # not working
    # error: NoSuchElementException: Message: no such element: Unable to locate element

    # root_element: WebElement = root_driver.find_element(By.CSS_SELECTOR, '*')  # worked but only got <style>
    # print(f"{root_element.get_attribute('outerHTML')}")
    for root_element in root_driver.find_elements(By.CSS_SELECTOR, ':host > *'):
        print(f"{root_element.get_attribute('outerHTML')}")