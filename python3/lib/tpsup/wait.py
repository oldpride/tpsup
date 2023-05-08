import time
from pprint import pformat
from tpsup.util import print_exception


def wait_for_max_try(maxTry, runFunction, param):
    while maxTry:
        print(f'{maxTry} times left')
        try:
            return runFunction(param)
        except Exception as e:
            print_exception(e)
            time.sleep(1)
            maxTry -= 1


def test_actions():
    import tpsup.seleniumtools
    from urllib.parse import urlparse

    driver = tpsup.seleniumtools.get_driver(host_port="localhost:19999")

    url = 'http://www.google.com/'
    driver.get(url)
    search_box = wait_for_max_try(
        5, driver.find_element_by_xpath, '//input[@name="q"]')

    search_box.clear()
    search_box.send_keys('ChromeDriver')

    # the following are the same
    # search_box.send_keys(webdriver.common.keys.Keys.RETURN)
    search_box.submit()

    for tag_a in driver.find_elements_by_tag_name('a'):
        link = None
        try:
            url = tag_a.get_attribute('href')
        # except NoSuchElementException as e:
        except NoSuchElementException:
            pass
        else:
            # print(f'url={url}')
            print(f'hostname = {urlparse(url).hostname}')

    for tag_a in driver.find_elements_by_tag_name('a'):
        link = None
        try:
            url = tag_a.get_attribute('href')
        # except NoSuchElementException as e:
        except NoSuchElementException:
            pass
        else:
            # print(f'url={url}')
            print(f'hostname = {urlparse(url).hostname}')

    driver.quit()


def main():
    test_actions()


if __name__ == '__main__':
    main()
