#!/usr/bin/env python

from glob import glob
import os
import re
import sys
import argparse
import textwrap
from pprint import pprint, pformat
from pywinauto.application import Application
from tpsup.pwatools import explore_child

prog = os.path.basename(sys.argv[0]).replace('_cmd.py', '')

usage = textwrap.dedent("""
    usage:
        {prog} title_regex_pattern
                            
        explore windows UIA using pywinauto.
    """)

examples = textwrap.dedent(f"""
    examples:
        run a notepad in windows, 
            notepad tianjunk
        
        {prog} .*tianjunk.*
                           
    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    # 'pattern', default=None, action='store', help='regex pattern')
    '-m', dest='MatchPatterns', default=[], action="append", help='extra MatchPatterns')

parser.add_argument(
    # 'pattern', default=None, action='store', help='regex pattern')
    '-x', dest='ExcludePatterns', default=[], action="append", help='extra ExcludePatterns')

parser.add_argument(
    'remaining_args',
    # 0 or more positional arguments. can handle intermixed options and positional args.
    nargs='*',
    help='should be only one positional argument, the title regex pattern')

parser.add_argument(
    '-v', '--verbose', dest="verbose", action='count', default=0,
    help="verbose mode. -v -v for more verbose")

args = vars(parser.parse_args())

verbose = args['verbose']

if verbose:
    print(f'args={pformat(args)}', file=sys.stderr)

if not args['remaining_args'] or len(args['remaining_args']) != 1:
    print("wrong number of positional args")
    print(usage)
    print
    print(examples)
    sys.exit(1)


opt = {}

title_regex = args['remaining_args'][0]

if verbose:
    print(f'opt={pformat(opt)}', file=sys.stderr)

app = Application(
    # backend="win32", # win32 is the default.
    backend="uia", # uia is modern and preferred.
)

print(f"Connecting app with title_re=\"{title_regex}\"...")

app.connect(title_re=title_regex, timeout=10)

print(f"Connected to app")

explore_child(app)
