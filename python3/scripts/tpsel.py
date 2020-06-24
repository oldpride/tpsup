#!/usr/bin/env python

import argparse
import os
import sys
import textwrap
from pprint import pformat
from urllib.parse import urlparse
import tpsup.env
import tpsup.seleniumtools
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

prog = os.path.basename(sys.argv[0])

my_env = tpsup.env.Env()
my_env.adapt()
home_dir = my_env.home_dir
system = my_env.system

driverlog = home_dir + '/selenium_chromedriver.log'
# driver log on Windows must use Windows path, eg, C:/Users/tian/test.log.
# Even when we run the script from Cygwin or GitBash, we still need to use Windows path.

usage = textwrap.dedent(f"""
    run selenium test
    
    +----------+      +--------------+     +----------------+
    | selenium +----->+ chromedriver +---->+ chrome browser +---->internet
    +----------+      +--------------+     +----------------+
    
    selenium will always start a chromedriver locally.
    For Linux
        chromedriver should be in the path or at ~
        chromium-browser should be in path
    
    For Windows, 
        chromedriver.exe should be in the PATH or at C:/users/<current_user>
        chrome.exe       should be in the PATH or at C:/Program Files (x86)/Google/Chrome/Application

    """)

examples = textwrap.dedent(f""" 
examples:
    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=usage,
    # formatter_class=argparse.RawTextHelpFormatter, # this honors \n but messed up indents
    epilog=examples)

parser.add_argument(
    '--headless', action='store_true', default=False,
    help="headless")

parser.add_argument(
    '-v', '--verbose', default=0, action="count",
    help='verbose level: -v, -vv, -vvv')

default_hostport = "localhost:19999"

parser.add_argument(
    '-hp', '--host_port', default=default_hostport,
    help="port of the browser. default to " + f"{default_hostport}")

parser.add_argument(
    '-ba', '--browserArgs', action="append", default=[],
    help='extra args to browser command, eg, -ba proxy-pac-url=http://pac.abc.net. can set multiple times.')

parser.add_argument(
    '-driver', dest="driver", default="chromedriver", action='store',
    help="driver executable file, eg, 'chromedriver78', default 'chromedriver', must be in PATH. Can also use path, "
         "for example, "
         "./chromedriver. we use this in case chromedriver and chrome browser's version mismatch.")

parser.add_argument(
    '-driverlog', dest="driverlog", default=driverlog, action='store',
    help="driver log, driver log on Windows must use Windows path, eg, C:/Users/tian/test.log. Even when we run the "
         "script from Cygwin or GitBash, we still need to use Windows path. "
         f"On this host, default to {driverlog}")

args = vars(parser.parse_args())

if args['verbose']:
    sys.stderr.write("args =\n")
    sys.stderr.write(pformat(args) + "\n")

seleniumEnv = tpsup.seleniumtools.SeleniumEnv(**args)

driver = seleniumEnv.get_driver()

if driver is None:
    sys.exit(1)

seleniumEnv.delay_for_viewer()  # give 1 sec to let the tail set up

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

for tag_a in driver.find_elements_by_tag_name('a'):
    link = None
    try:
        url = tag_a.get_attribute('href')
    except NoSuchElementException as e:
        pass
    else:
        # print(f'url={url}')
        print(f'hostname = {urlparse(url).hostname}')

seleniumEnv.quit()

print(f'driverlog file {seleniumEnv.driverlog}')
print(f'chromedir dir  {seleniumEnv.chromedir}')
