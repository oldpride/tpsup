import re

import argparse
import sys
from pprint import pformat
from inspect import currentframe, getframeinfo

import tpsup.seleniumtools
from selenium.common.exceptions import NoSuchElementException
from urllib.parse import urlparse
from tpsup.lock import EntryBook
from tpsup.util import print_exception, tplog


def run(seleniumEnv: tpsup.seleniumtools.SeleniumEnv, **opt):
    username = "lca_editor"  # change this to the username associated with your account
    verbose = opt.get('verbose', 0)
    mod_file = opt.get('mod_file', 'mod_file')
    argList = opt.get('argList', [])

    if verbose:
        sys.stderr.write(f"{mod_file}argList=\n")
        sys.stderr.write(pformat(argList) + "\n")

    parser = argparse.ArgumentParser(
        prog=mod_file,
    )
    parser.add_argument(
        '-u', dest='username', default=username, action='store',
        help='login user')
    args = vars(parser.parse_args(argList))

    if not verbose:
        verbose = args.get('verbose', 0)

    if verbose:
        tplog(f"args = {pformat(args)}")

    username = args['username']

    entryBook = EntryBook()
    password = entryBook.get_entry_by_key(username).get('decoded')

    driver = seleniumEnv.get_driver()

    # print(f'driver.title={driver.title}')

    url = 'https://livingstonchinese.org/'
    driver.get(url)

    expected_url = "https://livingstonchinese.org/LCA2/"
    actual_url = driver.current_url
    assert expected_url == actual_url

    seleniumEnv.delay_for_viewer()  # give 1 sec to let the tail set up

    # https://dev.to/endtest/a-practical-guide-for-finding-elements-with-selenium-4djf
    # in chrome browser, find the interested spot, right click -> inspect, this will bring up source code,
    # in the source code window, right click -> copy -> ...
    found_logout = True
    need_to_login = False

    logout_elem = None
    logout_css_selector = '#login-form > div.logout-button > input.btn.btn-primary'

    try:
        logout_elem = driver.find_element_by_css_selector(logout_css_selector)
    except NoSuchElementException:
        found_logout = False

    if found_logout:
        tplog(
            f"found logout button, meaning someone already logged in. css_selector='{logout_css_selector}'")
        need_to_logout = True
        greeting_text = None
        greeting_css = '#login-form > div.login-greeting'
        try:
            greeting_elem = driver.find_element_by_css_selector(greeting_css)
            if verbose:
                attrs = seleniumEnv.get_attrs(greeting_elem, method='bs4')
                tplog(f"attrs by bs4 = {pformat(attrs)}")
                attrs = seleniumEnv.get_attrs(greeting_elem, method='js')
                tplog(f"attrs by js = {pformat(attrs)}")
            greeting_text = greeting_elem.text
            tplog(f"greeting_text='{greeting_text}' at css='{greeting_css}'")
        except Exception as e:
            print_exception(e)
            tplog(
                f"cannot find greeting_text at css='{greeting_css}'. need to log out")
        if greeting_text:
            greeting_pattern = "^Hi (.+),"
            m = re.search(greeting_pattern, greeting_text)
            if m:
                username = m.group(1)
                expected_username = "LCA Editor Tester"
                if not username == expected_username:
                    tplog(
                        f"username='{username}' did not match expected username='{expected_username}'. need to log out")
                else:
                    need_to_logout = False
                    tplog(
                        f"username='{username}' matched expected username='{expected_username}'. no need to log in again")
            else:
                tplog(f"greeting_text='{greeting_text}', not matching expected greeting_pattern='{greeting_pattern}'. "
                      f"need to log out")
        else:
            tplog(
                f"cannot find greeting_text at css_selector={greeting_css}. need to log out")

        if need_to_logout:
            need_to_login = True
            logout_elem.click()
            seleniumEnv.delay_for_viewer(1)
    else:
        tplog(f"seems nobody logged in. we will login.")
        need_to_login = True

    if need_to_login:
        # from Edge/Chrome, right click the item -> inspect
        login_elem = driver.find_element_by_id('modlgn-username')
        login_elem.send_keys(username)
        seleniumEnv.delay_for_viewer(1)  # delay to mimic humane slowness
        password_elem = driver.find_element_by_id('modlgn-passwd')
        password_elem.send_keys(password)

        # frameinfo = getframeinfo(currentframe())
        # print(frameinfo.filename, frameinfo.lineno, file=sys.stderr)  # print line number

        # from Edge/Chrome, right click the item -> inspect
        # because login button has no "id", so I used xpath. xpath is very sensitive to changes in the page
        driver.find_element_by_xpath(
            '/html/body/div[1]/div/div/div/div[1]/form/div/div[4]/div/button').click()
        seleniumEnv.delay_for_viewer(1)  # delay to mimic humane slowness

        # this doesn't work as 'button' is a grand-child of form-login-sutmit
        # driver.find_element_by_id('form-login-submit').click()

    # frameinfo = getframeinfo(currentframe())
    # print(frameinfo.filename, frameinfo.lineno, file=sys.stderr)

    xpath = '//*[@id=\"login-form\"]'
    elem = driver.find_element_by_xpath('//*[@id=\"login-form\"]')
    welcomeText = elem.text

    # frameinfo = getframeinfo(currentframe())
    # print(frameinfo.filename, frameinfo.lineno, file=sys.stderr)

    tplog(f"We see: {welcomeText}")
    # assert re.search("^Hi ", welcomeText)
    error = None
    pattern = "^Hi "
    if not re.search(pattern, welcomeText):
        error = f"xpath='{xpath}' failed to match pattern '{pattern}'"

    result = {'error': error, 'data': welcomeText}

    return result
