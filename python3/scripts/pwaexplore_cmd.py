#!/usr/bin/env python

from glob import glob
import os
import re
import sys
import argparse
import textwrap
from pprint import pformat
from tpsup.pwatools import explore

prog = os.path.basename(sys.argv[0]).replace('_cmd.py', '')

usage = textwrap.dedent("""
    usage:
        {prog} title_regex_pattern
                            
        explore windows UIA using pywinauto.
    """)

examples = textwrap.dedent(f"""
    examples:
        1: test notepad
            {prog} start="notepad c:/users/tian/tianjunk" connect="title_re=.*tianjunk.*"

        2: test putty
            {prog} start="putty -load wsl" "type=siteenv{{ENTER}}" quit
    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    'remaining_args',
    # 0 or more positional arguments. can handle intermixed options and positional args.
    nargs='*',
    help='should be only one positional argument, the title regex pattern')

parser.add_argument(
    '-v', '--verbose', dest="verbose", action='count', default=0,
    help="verbose mode. -v -v for more verbose")

parser.add_argument(
    '-d', '--debug', dest="debug", action='count', default=0,
    help="debug mode. -d -d for more debug information")

parser.add_argument(
    '-sc', '--script', dest="script", action='store', default=None,
    help="script file to run after connected to the app window")

parser.add_argument(
    '-be', '--backend', dest="backend", action='store', default="uia",
    help="backend to use for the application. can be 'win32' or 'uia'. default is 'uia'")

args = vars(parser.parse_args())

verbose = args['verbose']
debug = args['debug']

if verbose or debug:
    print(f'args={pformat(args)}', file=sys.stderr)

if not args['remaining_args']:
    print("wrong number of positional args")
    print(usage)
    print
    print(examples)
    sys.exit(1)

args["init_steps"] = args['remaining_args']

if verbose or debug:
    print(f'args={pformat(args)}', file=sys.stderr)

explore(**args)
