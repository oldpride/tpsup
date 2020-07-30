import re

import tpsup.seleniumtools
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from urllib.parse import urlparse

from tpsup.lock import EntryBook


def run(seleniumEnv: tpsup.seleniumtools.SeleniumEnv):
    driver = seleniumEnv.get_driver()

    # print(f'driver.title={driver.title}')

    url = 'https://livingstonchinese.org/'
    driver.get(url)

    expected_url = "https://livingstonchinese.org/LCA2/"
    actual_url = driver.current_url
    assert expected_url == actual_url

    seleniumEnv.delay_for_viewer()  # give 1 sec to let the tail set up

    entryBook = EntryBook()
    username = "lca_editor"  # change this to the username associated with your account
    password = entryBook.get_entry_by_key(username).get('decoded')

    # https://dev.to/endtest/a-practical-guide-for-finding-elements-with-selenium-4djf
    # in chrome browser, find the interested spot, right click -> inspect, this will bring up source code,
    # in the source code window, right click -> copy -> ...

    # from Edge/Chrome, right click the item -> inspect
    driver.find_element_by_id('modlgn-username').send_keys(username)
    seleniumEnv.delay_for_viewer(1)  # delay to mimic humane slowness
    driver.find_element_by_id('modlgn-passwd').send_keys(password)

    # from Edge/Chrome, right click the item -> inspect
    # because login button has no "id", so I used xpath. xpath is very sensitive to changes in the page
    driver.find_element_by_xpath('/html/body/div[1]/div/div/div/div[1]/form/div/div[4]/div/button').click()
    seleniumEnv.delay_for_viewer(1) # delay to mimic humane slowness

    # this doesn't work as 'button' is a grand-child of form-login-sutmit
    # driver.find_element_by_id('form-login-submit').click()

    elem = driver.find_element_by_xpath('//*[@id=\"login-form\"]')
    welcomeText = elem.text

    print(f"We see: {welcomeText}")
    assert re.search("^Hi ", welcomeText)