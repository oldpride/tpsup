#!/usr/bin/env python

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
# find_element_by_name('q') is replaced with find_element(By.NAME, 'q')
from selenium.webdriver.common.by import By
from urllib.parse import urlparse

import argparse
import sys
import textwrap
from pprint import pformat
import os
import platform
import re

prog = os.path.basename(sys.argv[0])

home_dir = os.path.expanduser("~")
uname = platform.uname()
system = uname.system

driverlog = home_dir + '/selenium_chromedriver.log'
chromedir = home_dir + '/chrome_test'
# driver log on Windows must use Windows path, eg, C:/Users/tian/test.log. Even when we
# run the script from Cygwin or GitBash, we still need to use Windows path.

usage = textwrap.dedent(f"""
    run selenium test
    
    +----------+      +--------------+     +----------------+
    | selenium +----->+ chromedriver +---->+ chrome browser +---->internet
    +----------+      +--------------+     +----------------+
    
    selenium will always start a chromedriver locally.
    
    {prog} auto
    selenium will also start a local browser.

    {prog} host:port
    selenium will connect to an existing running browser, local or remote.
    
    For Windows, 
        because Windows automatically upgrade chrome.exe, making it incompatible with non-auto-graded
        chromedriver.exe. therefore, we save a static version of chrome.exe.
        
        the chromedriver.exe should be in the PATH or at C:/users/<current_user>
        the chrome.exe       should be in the PATH or at C:/users/<current_user>/Chrome/Application
        
        Don't use the system path C:/Program Files (x86)/Google/Chrome/Application/chrome.exe

    """)

examples = textwrap.dedent(f""" 
examples:
    3 ways to run the browser

    1. let selenium to start a local browser automatically
    {prog} auto
    {prog} -ba proxy-pac-url=http://pac.abc.net auto

    2. start Chrome (c1) on localhost with debug port 9222.
    From Linux,
        /usr/bin/chromium-browser --no-sandbox --disable-dev-shm-usage --window-size=960,540 \
        --user-data-dir=~/chrome_test --remote-debugging-port=9222 
        or 
        /opt/google/chrome/chrome --no-sandbox --disable-dev-shm-usage --window-size=960,540 \
        --user-data-dir=~/chrome_test --remote-debugging-port=9222
    From Cygwin or GitBash,
        "C:/users/$USERNAME/Chrome/Application/chrome.exe" --window-size=960,540 \
        --user-data-dir=C:/users/$USERNAME/chrome_test --remote-debugging-port=9222
    From cmd.exe, (have to use double quotes)
        "C:/Users/%USERNAME%/Chrome/Application/chrome.exe" --window-size=960,540 \
        --user-data-dir=C:/users/%USERNAME%/chrome_test --remote-debugging-port=9222

   {prog} localhost:9222

   3. start Chrome (c1) on remote PC with debug port 9222.

    +------------------+       +---------------------+
    | +---------+      |       |  +---------------+  |
    | |selenium |      |       |  |chrome browser +------->internet
    | +---+-----+      |       |  +----+----------+  |
    |     |            |       |       ^             |
    |     |            |       |       |             |
    |     v            |       |       |             |
    | +---+---------+  |       |  +----+---+         |
    | |chromedriver +------------>+netpipe |         |
    | +-------------+  |       |  +--------+         |
    |                  |       |                     |
    |                  |       |                     |
    |  Linux           |       |   PC                |
    |                  |       |                     |
    +------------------+       +---------------------+

    PC> "C:/Users/%USERNAME%/Chrome/Application/chrome.exe" \
    --remote-debugging-port=9222 --user-data-dir=%USERPROFILE%\\ChromeTest
    on the same remote PC, launch cygwin, in cygwin term: netpipe 9333 localhost:9222
   {prog} 192.168.1.164:9333

    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    # formatter_class=argparse.RawTextHelpFormatter, # this honors \n but messed up indents
    epilog=examples)

parser.add_argument(
    '--headless', action='store_true', default=False,
    help="headless")

parser.add_argument(
    '-v', '--verbose', default=0, action="count",
    help='verbose level: -v, -vv, -vvv')

parser.add_argument(
    'host_port', default=None,
    help="host:port of an browser. use 'auto' to let this script to start a browser")

parser.add_argument(
    '-ba', '--browserArgs', action="append",
    help='extra args to browser command, eg, -ba proxy-pac-url=http://pac.abc.net. can set multiple times.')

parser.add_argument(
    '-driver', dest="driver", default="chromedriver", action='store',
    help="driver, eg, 'chromedriver78', default 'chromedriver', must be in PATH. Can also use path, for example, "
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

if args['host_port'] == 'auto':
    if re.search("Windows", system, re.IGNORECASE):
        # Windows auto upgrade chrome.exe version, making it incompatible with chromedriver. therefore, we save a
        # static version of chrome.exe under C:\Users\%USERNAME%
        browser_options.binary_location = f'C:\\Users\\{os.environ["USERNAME"]}\\Chrome\\Application\chrome.exe'

    print('we will start a chromedriver which will start a browser')
    if headless:
        browser_options.add_argument("--headless")

    uname = platform.uname()
    system = uname.system

    # re.match() vs re.search()
    # re.match(): from the beginning of the string
    # re.search(): the whole string
    # re.match(".*abc", ...) = re.search("abc", ...)

    if re.search("Linux", system, re.IGNORECASE):
        browser_options.add_argument('--no-sandbox')  # to be able to run without root
        browser_options.add_argument('--disable-dev_shm-usage')  # to be able to run without root
        browser_options.add_argument('--window-size=960,540')
        browser_options.add_argument(f'--user-data-dir={chromedir}')
    elif re.search("Windows", system, re.IGNORECASE):
        # add chromedriver path on windows
        home_dir = os.path.expanduser("~")
        # print(f'home_dir={home_dir}')

        # sys.path is the module search path
        # sys.path += [ home_dir, r'C:\Program Files (x86)\Google\Chrome\Application']

        # chromedriver normally saved under home dir
        # static version (to avoid auto upgrade) of chrome is saved under homedir/Chrome/Application on Windows

        if re.search('cygwin|cygdrive', home_dir, re.IGNORECASE):
            # because cygwin's home dir is C:\cygwin64\home\<username>, likely not the normal windows's home
            # dir C:/users/<username>. use C:/users/<username> instead
            os.environ["PATH"] = os.pathsep.join([f'C:/Users/{os.environ["USERNAME"]}']) + os.pathsep + os.environ["PATH"]
            # PATH is only for chromedriver, not for chrome.exe. therefore, we don't add chrome path
            # os.environ["PATH"] += os.pathsep + os.pathsep.join(
            #     [f'C:/Users/{os.environ["USER"]}', f'C:/Users/{os.environ["USER"]}/Chrome/Application', r'C:\Program Files (x86)\Google\Chrome\Application'])
        else:
            os.environ["PATH"] = os.pathsep.join([home_dir]) + os.pathsep + os.environ["PATH"]
            # PATH is only for chromedriver, not for chrome.exe. therefore, we don't add chrome path
            # os.environ["PATH"] += os.pathsep + os.pathsep.join(
            #     [home_dir, home_dir + 'Chrome/Application', r'C:\Program Files (x86)\Google\Chrome\Application'])
        if args['verbose']:
            sys.stderr.write(f"sys.path={sys.path}\n")
            sys.stderr.write(f"home_dir={home_dir}\n")
            sys.stderr.write(f"PATH={os.environ['PATH']}\n")

    if args['browserArgs']:
        for arg in args['browserArgs']:
            browser_options.add_argument(f'--{arg}')
            # chrome_options.add_argument('--proxy-pac-url=http://pac.abc.net')  # to run with proxy
else:
    print(f'we will start a chrome driver which will connect to an existing browser at host:port={args["host_port"]}')
    browser_options.debugger_address = args["host_port"]

    # chromedriver and chrome browser version need to match
    #
    # to check chromedriver version
    # $ /usr/bin/chromedriver -v
    # ChromeDriver 79.0.3945.79 (29f75ce3f42b007bd80361b0dfcfee3a13ff90b8-refs/branch-heads/3945@{#916})
    #
    # to check browser version
    # on PC or Linux, open Chrome, Help->About Chrome, I see version 79.0....
    # on Linux only, chromium-browser --version

    # 1. test with a local browser
    # start the local chrome browser on linux
    # /usr/bin/chromium-browser --no-sandbox --disable-dev-shm-usage --window-size=960,540 \
    # --user-data-dir=/tmp/selenium_chrome_browser_dir --remote-debugging-port=9222

    # 2. test with a remote browser
    # start Chrome (c1) on PC with debug port 9222.
    # "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
    # --user-data-dir=%USERPROFILE%\ChromeTest
    #
    # on the same pc, start another chrome (c2) in normal way. In chrome c2, enter http://localhost:9222
    # you should see "inspected page". click the first link, it will bring up devTools.
    # Then in chrome c1, when go to an url, eg, google.com, chrome c2 will reflect this too
    #
    # chrome c1 can only accept local connection; cannot accept remote connection. Therefore, on the pc, start:
    #    netpipe 9333 localhost:9222
    # then have chromedriver pointing to pc_address:9333

# driver = webdriver.Chrome(driver_name,  # make sure chromedriver is in the PATH
#                           options=browser_options,  # for chrome browser
#                           service_args=driver_args,  # for chromedriver
#                           )

driver = webdriver.Chrome(driver_exe, options=browser_options, service_args=driver_args)

# driver = webdriver.Chrome(driver_name, service_args=driver_args)

time.sleep(1)  # give 1 sec to let the tail set up and also to throttle the headless mode

# print(f'driver.title={driver.title}')

url = 'http://www.google.com/'
driver.get(url)

if not headless:
    time.sleep(2)  # Let the user actually see something!

try:
    # https://dev.to/endtest/a-practical-guide-for-finding-elements-with-selenium-4djf
    # in chrome browser, find the interested spot, right click -> inspect, this will bring up source code,
    # in the source code window, right click -> copy -> ...
    # search_box = driver.find_element_by_name('q')
    search_box = driver.find_element(By.NAME, 'q')
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

#for tag_a in driver.find_elements_by_tag_name('a'):
for tag_a in driver.find_elements(By.TAG_NAME, 'a'):
    link = None
    try:
        url = tag_a.get_attribute('href')
    except NoSuchElementException as e:
        pass
    else:
        # print(f'url={url}')
        print(f'hostname = {urlparse(url).hostname}')

driver.quit()

# list all the log files for debug purpose
os.system("ls -ld /tmp/selenium_*")
