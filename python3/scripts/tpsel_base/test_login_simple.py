import argparse
import re
import sys
from pprint import pformat
import tpsup.seleniumtools_old
from tpsup.lock import EntryBook
from tpsup.utilbasic import tplog


def run(seleniumEnv: tpsup.seleniumtools_old.SeleniumEnv, **opt):
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

    print(f"We see: {welcomeText}")
    # assert re.search("^Hi ", welcomeText)
    error = None
    pattern = "^Hi "
    if not re.search(pattern, welcomeText):
        error = f"xpath='{xpath}' failed to match pattern '{pattern}'"

    result = {'error': error, 'data': welcomeText}

    return result
