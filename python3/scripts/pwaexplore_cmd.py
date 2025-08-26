#!/usr/bin/env python

from glob import glob
import os
import re
import sys
import argparse
import textwrap
from pprint import pformat
from tpsup.pwatools import explore_app

prog = os.path.basename(sys.argv[0]).replace('_cmd.py', '')

usage = textwrap.dedent("""
    usage:
        {prog} title_regex_pattern
                            
        explore windows UIA using pywinauto.
    """)

examples = textwrap.dedent(f"""
    examples:
        1:
            run a notepad in windows, 
                notepad tianjunk
            
            {prog} .*tianjunk.*
        2:    
            {prog} -c1 "putty -load wsl" "tianpc2 - PuTTY"
            {prog} -c2 "putty -load wsl" "tianpc2 - PuTTY"
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

parser.add_argument(
    '-d', '--debug', dest="debug", action='count', default=0,
    help="debug mode. -d -d for more debug information")

parser.add_argument(
    '-c1', '--command1', dest="command1", action='store', default=None,
    help="startup command to run before 1st connecting to the app window")

parser.add_argument(
    '-c2', '--command2', dest="command2", action='store', default=None,
    help="startup command to run if 1st connecting to the app window failed")

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

if not args['remaining_args'] or len(args['remaining_args']) != 1:
    print("wrong number of positional args")
    print(usage)
    print
    print(examples)
    sys.exit(1)

title_re = args['remaining_args'][0]
args['title_re'] = title_re
del args['remaining_args']

if verbose:
    print(f'args={pformat(args)}', file=sys.stderr)

explore_app(**args)
