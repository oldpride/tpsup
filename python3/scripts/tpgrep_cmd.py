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
                           
        {prog}      mypattern tpgrep_test*
        {prog}   -v mypattern tpgrep_test*
        {prog}    "abc1|def2" tpgrep_test*
        {prog} "^(abc1|def2)" tpgrep_test*

        # match multiple patterns in any order. use -m to specify extra patterns
        {prog} -m ab c1 tpgrep_test*
        # if we used normal egrep, we would have to do
        egrep (ab.*c1|c1.*ab) tpgrep_test*
        # it would be a nightmare to use egrep if we have more than 2 patterns.

        # recursive
        {prog} -r selenium .

        # file name only
        {prog} -l -r selenium .

    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    # 'pattern', default=None, action='store', help='regex pattern')
    'MatchPatterns', action="append", help='MatchPatterns')

parser.add_argument(
    # 'pattern', default=None, action='store', help='regex pattern')
    '-m', dest='MatchPatterns', action="append", help='extra MatchPatterns')

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
    '-r', dest='Recursive', action="store_true",
    default=False, help='recursive')

parser.add_argument(
    '-l', dest='FileNameOnly', action="store_true",
    default=False, help='print file name only')

parser.add_argument(
    '-E', dest='regex', action="store_true",
    default=False, help='currently not used. for compatibility only')

parser.add_argument(
    '-i', dest='CaseInsensitive', action="store_true",
    default=False, help='case-insensitive')

parser.add_argument(
    '-d', dest='verbose', default=0, action="count",
    help='verbose mode. -d, -dd, -ddd, ...')

args = vars(parser.parse_args())

verbose = args['verbose']

if verbose:
    print(f'args={pformat(args)}', file=sys.stderr)

opt = {}
if args['exclusive']:
    opt['ExcludePatterns'] = args['MatchPatterns']
else:
    opt['MatchPatterns'] = args['MatchPatterns']

# files = glob(args['file'])
files = []
if args['remainingArgs']:
    files.extend(args['remainingArgs'])
else:
    files.append('-')

opt['print'] = True
opt['verbose'] = args['verbose']
opt['CaseInsensitive'] = args['CaseInsensitive']
opt['Recursive'] = args['Recursive']
opt['FileNameOnly'] = args['FileNameOnly']

grep(files, **opt)
