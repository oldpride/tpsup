#!/usr/bin/env python

# copied https://github.com/SeleniumHQ/seleniumhq.github.io/blob/trunk/examples/python/tests/getting_started/test_first_script.py#L6


from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService


def test_eight_components():
    driver_path = ChromeDriverManager().install()
    # driver_path = /Users/tian/.wdm/drivers/chromedriver/mac64/116.0.5845.179/chromedriver-mac-arm64/chromedriver
    print(f'driver_path = {driver_path}')
    driver = webdriver.Chrome(
        service=ChromeService(executable_path=driver_path))

    driver.get("https://www.selenium.dev/selenium/web/web-form.html")

    title = driver.title
    print(f'title = {title}')
    assert title == "Web form"

    driver.implicitly_wait(0.5)

    text_box = driver.find_element(by=By.NAME, value="my-text")
    submit_button = driver.find_element(by=By.CSS_SELECTOR, value="button")

    text_box.send_keys("Selenium")
    submit_button.click()

    message = driver.find_element(by=By.ID, value="message")
    value = message.text
    print(f'value = {value}')
    assert value == "Received!"

    driver.quit()


test_eight_components()
