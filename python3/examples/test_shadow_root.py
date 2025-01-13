#!/usr/bin/env python

# https://stackoverflow.com/questions/73563079

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchShadowRootException

import time as t
# import pandas as pd


chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument('disable-notifications')
chrome_options.add_argument("window-size=1280,720")

# webdriver_service = Service("chromedriver/chromedriver") ## path to where you saved chromedriver binary
# browser = webdriver.Chrome(service=webdriver_service, options=chrome_options)
browser = webdriver.Chrome(options=chrome_options)
actions = ActionChains(browser)
wait = WebDriverWait(browser, 20)
url = 'https://iltacon2022.expofp.com/'
browser.get(url)

all_elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, '//*')))
for el in all_elements:
    try:
        if el.shadow_root:
            print('found shadow root in', el.get_attribute('outerHTML'))
    except NoSuchShadowRootException:
        print('no shaddow root')