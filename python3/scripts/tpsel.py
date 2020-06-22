#!/usr/bin/env python

import time
import tpsup.env
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from urllib.parse import urlparse
import argparse
import sys
import textwrap
from pprint import pformat
import os
import re
from tpsup.nettools import is_tcp_open

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
    '-ba', '--browserArgs', action="append",
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

headless = args['headless']
driver_exe = args['driver']

if args['verbose']:
    cmd = 'ps -ef|grep chromedriver|grep -v grep'
    print(cmd)
    os.system(cmd)

driver_args = ["--verbose", f"--log-path={driverlog}"]  # for chromedriver

if args['verbose']:
    cmd = f"cat /dev/null {driverlog}"
    print(cmd)
    os.system(cmd)

    # --pid PID  exits when PID is gone
    # -F         retry file if it doesn't exist
    cmd = f"tail --pid {os.getpid()} -F -f {driverlog} &"
    print(cmd)
    os.system(cmd)

# chrome_options will be used on chrome browser's command line not chromedriver's commandline
browser_options = Options()

host_port = args["host_port"]
(host, port) = host_port.split(':')

# try to connect the browser in case already exists.
# by setting this, we tell chromedriver not to start a browser
browser_options.debugger_address = host_port

driver = None
sys.stderr.write(f'check browser port at {host_port}\n')
if is_tcp_open(host, port):
    sys.stderr.write(f'{host_port} is open. chromedriver is connecting to it\n')

    try:
        driver = webdriver.Chrome(driver_exe, options=browser_options, service_args=driver_args)
    except Exception as e:
        print(e)

if driver is None:
    # by doing one of the following, we tell chromedriver to start a browser
    browser_options.debugger_address = None
    # browser_options = Options() # reset the browser options

    if host != 'localhost' and host != '127.0.0.1' and host != '':
        sys.stderr.write("cannot connect remote browser. quit\n")
        sys.exit(1)
    else:
        sys.stderr.write("cannot connect local browser. we will start it up\n")

    if headless:
        browser_options.add_argument("--headless")

    if re.search("Linux", system, re.IGNORECASE):
        browser_options.add_argument('--no-sandbox')  # to be able to run without root
        browser_options.add_argument('--disable-dev_shm-usage')  # to be able to run without root
        browser_options.add_argument('--window-size=960,540')
        browser_options.add_argument('---user-data-dir=/tmp/selenium_chrome_browser_dir')
    elif re.search("Windows", system, re.IGNORECASE):
        os.environ["PATH"] += os.pathsep + os.pathsep.join(
            [home_dir, r'C:\Program Files (x86)\Google\Chrome\Application'])
        if args['verbose']:
            # print(sys.path)
            print(os.environ["PATH"])

    browser_options.add_argument(f'--remote-debugging-port={port}')
    # browser_options.add_argument(f'--remote-debugging-address=127.0.0.1')
    if args['browserArgs']:
        for arg in args['browserArgs']:
            browser_options.add_argument(f'--{arg}')
            # chrome_options.add_argument('--proxy-pac-url=http://pac.abc.net')  # to run with proxy

    driver = webdriver.Chrome(driver_exe,  # make sure chromedriver is in the PATH
                              options=browser_options,  # for chrome browser
                              service_args=driver_args,  # for chromedriver
                              )


time.sleep(1)  # give 1 sec to let the tail set up

# print(f'driver.title={driver.title}')

url = 'http://www.google.com/'
driver.get(url)

if not headless:
    time.sleep(2)  # Let the user actually see something!

try:
    # https://dev.to/endtest/a-practical-guide-for-finding-elements-with-selenium-4djf
    # in chrome browser, find the interested spot, right click -> inspect, this will bring up source code,
    # in the source code window, right click -> copy -> ...
    search_box = driver.find_element_by_name('q')
except NoSuchElementException as e:
    print(e)
else:
    search_box.clear()
    search_box.send_keys('ChromeDriver')

    # the following are the same
    search_box.send_keys(webdriver.common.keys.Keys.RETURN)
    # search_box.submit()
    if not headless:
        time.sleep(2)  # Let the user actually see something!

for tag_a in driver.find_elements_by_tag_name('a'):
    link = None
    try:
        url = tag_a.get_attribute('href')
    except NoSuchElementException as e:
        pass
    else:
        # print(f'url={url}')
        print(f'hostname = {urlparse(url).hostname}')

# because we want to keep the browser running, we don't run either of the following command which closes the browser
# driver.quit()
# driver.dispose()
# driver.close()

# list all the log files for debug purpose
os.system("ls -ld /tmp/selenium_*")
