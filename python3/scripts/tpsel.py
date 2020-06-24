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
    {prog} -dryrun         tpsel_test_google.py
    {prog}                 tpsel_test_google.py
    {prog} --headless      tpsel_test_google.py
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

parser.add_argument(
   '-dryrun', '--dryrun', dest='dryrun', action='store_true', default=False, help='dryrun mode')

parser.add_argument(
    'mod_files', default=[], action='append',
    help='selenium module files')

args = vars(parser.parse_args())

if args['verbose']:
    sys.stderr.write("args =\n")
    sys.stderr.write(pformat(args) + "\n")

seleniumEnv = tpsup.seleniumtools.SeleniumEnv(**args)

driver = seleniumEnv.get_driver()

if driver is None and not args['dryrun']:
    sys.exit(1)

for mod_file in args['mod_files']:
    with open(mod_file, 'r') as f:
        source = f.read()
        module = None
        try:
            module = load_module(source)
        except Exception as e:
            traceback.print_exc(file=sys.stderr) # e.printStackTrace equivalent in python
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
