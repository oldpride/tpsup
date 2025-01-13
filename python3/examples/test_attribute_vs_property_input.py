#!/usr/bin/env python

'''
https://developer.mozilla.org/en-US/docs/Web/WebDriver/Commands/GetElementProperty
the original code had a log problems, and the result was not reproducible.
2023/06/13
  $ siteenv
  $ p3env
  $ svenv
  $ python test_attribute_vs_property_input.py
   get_attribute = foobar (expected to be foo)
   get_property = foobar
why not working?
https://stackoverflow.com/questions/55844052
get_attribute(attribute_name)
   - This method will first try to return the value of a property with the 
     given name. 
   - If a property with that name doesn’t exist, it returns the value of the
    attribute with the same name. 
   - If there’s no attribute with that name, None is returned.
get_property(property_name)
   gets the given property of the element.
In HTML, tags may have attributes. 
When the browser parses the HTML to create DOM objects for tags, it recognizes
standard attributes and creates DOM properties from them.

So when an element has id or another standard attribute, the corresponding
property gets created. But that doesn’t happen if the attribute is non-standard.

Note: A standard attribute for one element can be unknown for another one. 
For instance, type is standard attribute for <input> tag, but not for <body> tag. 
Standard attributes are described in the specification for the corresponding
 element class.
'''


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
driver.get(inline("<input value=foo myattr=foo>"))
textbox = driver.find_element(webdriver.common.by.By.TAG_NAME, "input")
textbox.send_keys("bar")
textbox.set_attribute("value", "bar")

print(f'get_attribute("value") = {textbox.get_attribute("value")}')
print(f'get_property("value") = {textbox.get_property("value")}')
print(f'get_attribute("myattr") = {textbox.get_attribute("myattr")}')
print(f'get_property("myattr") = {textbox.get_property("myattr")}')
