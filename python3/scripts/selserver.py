#!/usr/bin/env python

import argparse
import os
import sys
import textwrap
from pprint import pformat
import tpsup.env
import tpsup.seleniumtools
from tpsup.util import load_module
import traceback
import time
import socketserver

prog = os.path.basename(sys.argv[0])

my_env = tpsup.env.Env()
my_env.adapt()
home_dir = my_env.home_dir
system = my_env.system

driverlog = home_dir + '/selenium_chromedriver.log'
# driver log on Windows must use Windows path, eg, C:/Users/tian/test.log.
# Even when we run the script from Cygwin or GitBash, we still need to use Windows path.

usage = textwrap.dedent(f"""
    run selenium test modules
    
    +----------+      +--------------+     +----------------+
    | selenium +----->+ chromedriver +---->+ chrome browser +---->internet
    +----------+      +--------------+     +----------------+
    
    selenium will always start a chromedriver locally.

    If there is a chrome browser already started at the host:port, this script will start a chromedriver
    and direct the chromedriver to connect to the host:port. After the script is done, the chromedriver
    will be automatically shut down but the browser will live on.

    If there is no browser at the host:port, this script will start a chromedriver, and the chromedriver
    will start a chrome browser which will listen at the host:port. chromedriver will shut down the
    browser when the script is done. The shutdown call is automatically registered, and so far no 
    successful practice to disable it.

    To manually start a local browser at port 19999
        From Linux,
            /usr/bin/chromium-browser --no-sandbox --disable-dev-shm-usage --window-size=960,540 \
            --user-data-dir=~/chrome_test --remote-debugging-port=19999 
        From Cygwin or GitBash,
            'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe' --window-size=960,540 \
            --user-data-dir=C:/users/$USERNAME/chrome_test --remote-debugging-port=19999
        From cmd.exe, (have to use double quotes)
            "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe" --window-size=960,540 \
            --user-data-dir=C:/users/%USERNAME%/chrome_test --remote-debugging-port=19999

    For Linux
        chromedriver should be in the path or at ~
        chromium-browser should be in path
    
    For Windows, 
        chromedriver.exe should be in the PATH or at C:/users/<current_user>
        chrome.exe       should be in the PATH or at C:/Program Files (x86)/Google/Chrome/Application

    """)

examples = textwrap.dedent(f""" 
examples:
    {prog} 29999 init.py

    platform specifics
        in Linux, Windows GitBash
            {prog} tpsel_test_google.py
        in Windows, cygwin, cmd.exe, or powerhell
            python {prog} tpsel_test_google.py
    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    epilog=examples,
    description=usage,
    # formatter_class=argparse.RawTextHelpFormatter, # this honors \n but messed up indents
    formatter_class=argparse.RawDescriptionHelpFormatter
    )

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

parser.add_argument(
   '-dryrun', '--dryrun', dest='dryrun', action='store_true', default=False, help='dryrun mode')

parser.add_argument(
    'listener_port', default=None, action='store',
    help='selserver listener port')

parser.add_argument(
    # this is the rest positional args, indicated by 'append'. nargs="*' means optional.
    # the default is actually [[]]. So when we process it, we cannot assume the List is always str.
    'init_mod_files', default=[], action='append', nargs='*',
    help='run these init files (.py) right after server starts up, eg, prep work. optional')

args = vars(parser.parse_args())

if args['verbose']:
    sys.stderr.write("args =\n")
    sys.stderr.write(pformat(args) + "\n")

seleniumEnv = tpsup.seleniumtools.SeleniumEnv(**args)

driver = seleniumEnv.get_driver()

if driver is None and not args['dryrun']:
    sys.exit(1)

for mod_file in args['init_mod_files']:
    if not mod_file:
        # as mentioned before, the default of args['init_mod_files'] is [[]]
        continue
    with open(mod_file, 'r') as f:
        source = f.read()
        module = None
        try:
            module = load_module(source)
        except Exception:
            traceback.print_exc(file=sys.stderr)  # e.printStackTrace equivalent in python
            module = None

        if module is None:
            sys.stderr.write(f"failed to compile: {mod_file}\n")
            continue

        if args['dryrun']:
            sys.stderr.write(f"dryrun mode: {mod_file} compiled successfully\n")
        else:
            sys.stderr.write(f"running: {mod_file}\n")
            module.run(seleniumEnv)

seleniumEnv.quit()
time.sleep(1)
seleniumEnv.print_running_drivers()

if args['verbose']:
    print(f'driverlog file {seleniumEnv.driverlog}')
    print(f'chromedir dir  {seleniumEnv.chromedir}')
