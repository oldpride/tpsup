#!/usr/bin/env python

from glob import glob
import os
import sys
import argparse
import textwrap
from pprint import pprint, pformat
from tpsup.greptools import grep

prog = os.path.basename(sys.argv[0]).replace('_cmd.py', '')

usage = textwrap.dedent("""
    usage:
        {prog} pattern file1 file2 ...
                            
        'grep' command implemented in python, so that we can run it on windows.
    """)

examples = textwrap.dedent(f"""
    examples:
                           
        {prog}      mypattern grep_test*
        {prog}   -v mypattern grep_test*
        {prog}    "abc1|def2" grep_test*
        {prog} "^(abc1|def2)" grep_test*

    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    'pattern', default=None, action='store', help='regex pattern')

# parser.add_argument(
#     'file', default='-', action='store',
#     help='file to grep')

parser.add_argument(
    # https://stackoverflow.com/questions/15583870
    # "argparse.REMAINDER" tells the argparse module to take the rest of the arguments in args,
    # when it finds the first argument it cannot match to the rest.
    'remainingArgs', nargs=argparse.REMAINDER,
    # this may not be desirable.
    # but the parser cannot handle intermixed options and positional args.
    help='optionally additonal files')

parser.add_argument(
    '-v', dest='exclusive', action="store_true",
    default=False, help='exclusive pattern')

parser.add_argument(
    '-E', dest='regex', action="store_true",
    default=False, help='currently not used. for compatibility only')

parser.add_argument(
    '-d', dest='verbose', action="store_true",
    default=False, help='verbose mode.')

args = vars(parser.parse_args())

verbose = args['verbose']

if verbose:
    print(f'args={pformat(args)}', file=sys.stderr)

opt = {}
if args['exclusive']:
    opt['ExcludePattern'] = args['pattern']
else:
    opt['MatchPattern'] = args['pattern']

# files = glob(args['file'])
files = []
if args['remainingArgs']:
    files.extend(args['remainingArgs'])
else:
    files.append('-')

opt['print'] = True
opt['verbose'] = args['verbose']

grep(files, **opt)
