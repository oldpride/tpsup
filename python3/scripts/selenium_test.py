#!/usr/bin/env python3

# https://chromedriver.chromium.org/getting-started


import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import argparse
import sys
import textwrap
from pprint import pprint, pformat
import os
import io

prog = os.path.basename(sys.argv[0])

usage = textwrap.dedent("""
    run selenium test
    """)

examples = textwrap.dedent(f""" 
examples:
    - let Selenium::Chrome to start a local browser automatically
   {prog} auto

    - start Chrome (c1) on localhost with debug port 9222.
    /usr/bin/chromium-browser --no-sandbox --disable-dev-shm-usage --window-size=960,540 \
    --user-data-dir=/tmp/selenium_chrome_browser_dir --remote-debugging-port=9222 
   {prog} local_browser

   - start Chrome (c1) on remote PC with debug port 9222.
    PC> "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe" \
    --remote-debugging-port=9333 --user-data-dir=%USERPROFILE%\\ChromeTest
    on the same remote PC, launch cygwin, in cygwin term: netpipe 9222 localhost:9333
   {prog} remote_browser

    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    'test', default=None,
    choices=['auto', 'local_browser', 'remote_browser'],
    help='specify the test')

parser.add_argument(
    '--headless', action='store_true', default=False,
    help="headless")

parser.add_argument(
    '-v', '--verbose', default=0, action="count",
    help='verbose level: -v, -vv, -vvv')

# parser.add_argument(
#     '-s', '--StringInput', action="store_true",
#     help='input is a string on command line')
#
# parser.add_argument(
#     '-d', '-delimiter', dest="FixDelimiter", default=None, action='store',
#     help="input FIX delimiter, default to ','")
#
# parser.add_argument(
#     '-dict', dest="FixDict", default=None, action='store',
#     help="extra dictionary to resolve fix tags and values")

args = vars(parser.parse_args())

if args['verbose']:
    sys.stderr.write("args =\n")
    sys.stderr.write(pformat(args) + "\n")

headless = args['headless']

chromedriver_service_args = ["--verbose", "--log-path=/tmp/chromedriver.log"]  # for chromedriver

# chrome_options will be used on chrome browser's command line not chromedriver's commandline
chrome_options = Options()

if args['test'] == 'auto':
    # we will start up a local chromedriver, which will in turn start a local chrome browser.

    if headless:
        chrome_options.add_argument("--headless")

    chrome_options.add_argument('--no-sandbox')  # to be able to run without root
    chrome_options.add_argument('--disable-dev_shm-usage')  # to be able to run without root
    chrome_options.add_argument('-window-size=960,540 --user-data-dir=/tmp/selenium_chrome_browser_dir')
    # chrome_options.add_argument('--proxy-pac-url=http://pac.abc.net')  # to run with proxy

elif args['test'] == 'local_browser':
    # we will start local chromedriver which will connect to an existing local chrome browser

    print('we will use local browser')

    # this will tell chromedriver to connect a remote browser, not starting one locally
    chrome_options.debugger_address = 'localhost:9222'

    # chromedriver and chrome browser version must match
    # $ /usr/bin/chromedriver -v
    # ChromeDriver 79.0.3945.79 (29f75ce3f42b007bd80361b0dfcfee3a13ff90b8-refs/branch-heads/3945@{#916})
    # on PC, open Chrome, Help->About Chrome, I see version 79.0....
    # Matched !!!

    # start the local chrome browser
    # /usr/bin/chromium-browser --no-sandbox --disable-dev-shm-usage --window-size=960,540 \
    # --user-data-dir=/tmp/selenium_chrome_browser_dir --remote-debugging-port=9222

elif args['test'] == 'remote_browser':
    # we will start a chromedriver which will connect to an existing chrome browser on a remote PC

    # this will tell chromedriver to connect a remote browser, not starting one locally
    chrome_options.debugger_address = '192.168.1.164:9333'

    # chromedriver and chrome browser version must match
    # $ /usr/bin/chromedriver -v
    # ChromeDriver 79.0.3945.79 (29f75ce3f42b007bd80361b0dfcfee3a13ff90b8-refs/branch-heads/3945@{#916})
    # on PC, open Chrome, Help->About Chrome, I see version 79.0....
    # Matched !!!

    # start Chrome (c1) on PC with debug port 9222.
    # "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=%USERPROFILE%\ChromeTest

    # on the same pc, start another chrome (c2) in normal way. In chrome c2, enter http://localhost:9222
    # you should see "inspectable page". click the first link, it will bring up devTools.
    # Then in chrome c1, when go to an url, eg, google.com, chrome c2 will reflect this too

    # chrome c1 can only accept local connection; cannot accept remote connection. Therefore, on the pc, start:
    #    netpipe 9333 localhost:9222
    # then have chromedriver pointing to pc_address:9333

driver = webdriver.Chrome('chromedriver',  # make sure chromedriver is in the PATH
                          options=chrome_options,  # for chrome browser
                          service_args=chromedriver_service_args,  # for chromedriver
                          )

print(f'driver.title={driver.title}')

url = 'http://www.google.com/'
driver.get(url)

if not headless:
    time.sleep(5)  # Let the user actually see something!

try:
    search_box = driver.find_element_by_name('q')
except NoSuchElementException as e:
    print(e)
else:
    search_box.send_keys('ChromeDriver')
    search_box.submit()
    if not headless:
        time.sleep(5)  # Let the user actually see something!
driver.quit()
