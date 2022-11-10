import re
import time

import behave_webdriver
from behave import then, when
from selenium.webdriver.chrome.options import Options
from tpsup.lock import EntryBook

entryBook = EntryBook()
username = "lca_editor"  # change this to the username associated with your account
password = entryBook.get_entry_by_key(username).get('decoded')


def before_all(context):
    # context.behave_driver = behave_webdriver.Chrome()

    # for headless
    # 1. this still pop up a blank browser
    # context.behave_driver = behave_webdriver.Chrome().headless()

    # 2. this works; no browser popped up
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')  # Last I checked this was necessary.
    context.behave_driver = behave_webdriver.Chrome(chrome_options=options)


def after_all(context):
    # cleanup after tests run
    context.behave_driver.quit()

# mimic
# https://help.crossbrowsertesting.com/selenium-testing/frameworks/behave/

# @given('I go to my login form')
# def go_to_login_form(context):
#     context.driver.get('http://crossbrowsertesting.github.io/login-form.html')


# @then('the title should be {text}')
# def verify_title(context, text):
#     title = context.driver.title
#     try:
#         assert "Login Form - CrossBrowserTesting.com" == title
#     except AssertionError as e:
#         set_score(context, 'fail')

@when('I enter my credentials')
def enter_credentials(context):
    # from Edge/Chrome, right click the item -> inspect
    context.behave_driver.find_element_by_id('modlgn-username').send_keys(username)
    context.behave_driver.find_element_by_id('modlgn-passwd').send_keys(password)


@when('I click login')
def click_login(context):
    # from Edge/Chrome, right click the item -> inspect
    # because login button has no "id", so I used xpath. xpath is very sensitive to changes in the page
    context.behave_driver.find_element_by_xpath('/html/body/div[1]/div/div/div/div[1]/form/div/div[4]/div/button').click()

    # this doesn't work as 'button' is a grand-child of form-login-sutmit
    # context.behave_driver.find_element_by_id('form-login-submit').click()


@then('I should see the login message')
def see_login_message(context):
    # got error with this.
    # context.behave_driver.implicitly_wait("2")

    time.sleep(2)

    elem = context.behave_driver.find_element_by_xpath('//*[@id=\"login-form\"]')
    welcomeText = elem.text

    # to print out from behave.
    #      1. need "\n\n" at the end
    #      2. behave . --no-capture
    # https://stackoverflow.com/questions/25150404/how-can-i-see-print-statements-in-behave-bdd
    print(f"{welcomeText}\n\n")
    assert re.search("^Hi ", welcomeText)

