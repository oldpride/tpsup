#!/usr/bin/env python

from glob import glob
import os
import sys
import argparse
import textwrap
from pprint import pprint, pformat
from tpsup.greptools import grepl

prog = os.path.basename(sys.argv[0]).replace('_cmd.py', '')

usage = textwrap.dedent("""
    usage:
        {prog} -m pattern1 -m pattern2 file1 file2 ...
                            
        'grep' command implemented in python, so that we can run it on windows.
    """)

examples = textwrap.dedent(f"""
    examples:
                           
        {prog} -m abc1 -m def1 grep_test*

    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

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
    '-d', dest='verbose', action="store_true",
    default=False, help='verbose mode.')

parser.add_argument(
    '-m', dest='MatchPatterns', action="append", help='MatchPatterns')

args = vars(parser.parse_args())

verbose = args['verbose']

if verbose:
    print(f'args={pformat(args)}', file=sys.stderr)

opt = {}

opt['MatchPatterns'] = args['MatchPatterns']

# files = glob(args['file'])
files = []
if args['remainingArgs']:
    files.extend(args['remainingArgs'])
else:
    files.append('-')

opt['print'] = True
opt['verbose'] = args['verbose']

grepl(files, **opt)
