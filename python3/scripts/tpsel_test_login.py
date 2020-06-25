import tpsup.seleniumtools
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from urllib.parse import urlparse


def run(seleniumEnv: tpsup.seleniumtools.SeleniumEnv):
    driver = seleniumEnv.get_driver()

    # print(f'driver.title={driver.title}')

    url = 'http://www.costco.com/'
    driver.get(url)

    seleniumEnv.delay_for_viewer()  # give 1 sec to let the tail set up

    # https://dev.to/endtest/a-practical-guide-for-finding-elements-with-selenium-4djf
    # in chrome browser, find the interested spot, right click -> inspect, this will bring up source code,
    # in the source code window, right click -> copy -> ...

    driver.find_element_by_css_selector("#header_sign_in").click()
