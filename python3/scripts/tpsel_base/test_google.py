import tpsup.seleniumtools_old
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from urllib.parse import urlparse


def run(seleniumEnv: tpsup.seleniumtools_old.SeleniumEnv, **opt):
    driver = seleniumEnv.get_driver()

    # print(f'driver.title={driver.title}')

    url = 'http://www.google.com/'
    driver.get(url)

    seleniumEnv.delay_for_viewer()  # give 1 sec to let the tail set up

    # https://dev.to/endtest/a-practical-guide-for-finding-elements-with-selenium-4djf
    # in chrome browser, find the interested spot, right click -> inspect, this will bring up source code,
    # in the source code window, right click -> copy -> ...
    search_box = driver.find_element_by_name('q')

    search_box.clear()
    search_box.send_keys('ChromeDriver')

    # the following are the same
    search_box.send_keys(webdriver.common.keys.Keys.RETURN)
    # search_box.submit()

    seleniumEnv.delay_for_viewer()  # give 1 sec to let the tail set up
    # urls = list(str) # this gives error: TypeError: 'type' object is not iterable
    urls = []

    for tag_a in driver.find_elements_by_tag_name('a'):
        link = None
        try:
            url = tag_a.get_attribute('href')
        except NoSuchElementException as e:
            pass
        else:
            # print(f'url={url}')
            urls.append(url)
            print(f'hostname = {urlparse(url).hostname}')

    error = None

    result = {'error': error, 'data': urls}
    return result
