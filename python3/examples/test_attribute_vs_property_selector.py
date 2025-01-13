#!/usr/bin/env python

# https://stackoverflow.com/questions/43627340
#   An attribute is a static attribute of a given DOM node,
#   a property is a computed property of the DOM node object.
# example
#   a property would be the checked state of a checkbox, or value or an input field.
#   an attribute would be href of an anchor tag or the type of an input DOM.
# 2023/06/13
#   $ siteenv
#   $ p3env
#   $ svenv
#   $ python test_attribute_vs_property_selector.py


import os
import urllib
from selenium import webdriver
from shutil import which


def inline(doc):
    return "data:text/html;charset=utf-8,{}".format(urllib.parse.quote(doc))


browser_options = webdriver.chrome.options.Options()

chrome_path = which("chrome")
if not chrome_path:
    chrome_path = which("google-chrome")

if not chrome_path:
    raise Exception("Chrome not found in path.")

browser_options.binary_location = chrome_path

log_base = os.environ.get("HOME")
driverlog = os.path.join(log_base, "selenium_driver.log")
chromedir = os.path.join(log_base, "selenium_browser")
chromedir = chromedir.replace('\\', '/')
browser_options.add_argument(f"--user-data-dir={chromedir}")

driver = webdriver.Chrome(options=browser_options)
inline_string = inline('''
<a href="https://google.com" id="hello">Hello World</a>
<p>
<input type="checkbox" id="foo" checked>
<p>
<input type="text" id="bar" value="cheesecake">
''')

print(f'inline_string = {inline_string}')

driver.get(inline_string)
selector = driver.find_element(webdriver.common.by.By.ID, "hello")
# sele

# print(f'get_attribute = {textbox.get_attribute("value")}')
# print(f'get_property = {textbox.get_property("value")}')
