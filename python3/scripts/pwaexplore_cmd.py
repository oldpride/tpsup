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

parser.add_argument(
    '-d', '--debug', dest="debug", action='count', default=0,
    help="debug mode. -d -d for more debug information")


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

opt = {
    'debug': debug,
    'verbose': verbose,
    'MatchPatterns': args['MatchPatterns'],
    'ExcludePatterns': args['ExcludePatterns'],
    'title_re': title_re,
}

if verbose:
    print(f'opt={pformat(opt)}', file=sys.stderr)

explore_app(**opt)
