#!/usr/bin/env python

from glob import glob
import os
import sys
import argparse
import textwrap
from pprint import pprint, pformat
from tpsup.greptools import tpgrep

prog = os.path.basename(sys.argv[0]).replace('_cmd.py', '')

usage = textwrap.dedent("""
    usage:
        {prog} pattern file1 file2 ...
                            
        'grep' command implemented in python, so that we can run it on windows.
    """)

examples = textwrap.dedent(f"""
    examples:
                           
        {prog}      mypattern ptgrep_test*
        {prog}   -v mypattern ptgrep_test*
        {prog}    "abc1|def2" ptgrep_test*
        {prog} "^(abc1|def2)" ptgrep_test*

        echo abc1 | {prog} abc
        echo abc1 | {prog} -v abc

        # match multiple patterns in any order. use -m to specify extra patterns
        {prog} -m ab c1 ptgrep_test*
        # if we used normal egrep, we would have to do
        egrep (ab.*c1|c1.*ab) ptgrep_test*
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
    '-m', dest='MatchPatterns', default=[], action="append", help='extra MatchPatterns')

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

parser.add_argument(
    'pattern_and_files',
    # 0 or more positional arguments. can handle intermixed options and positional args.
    nargs='*',
    help='optionally additonal files')

args = vars(parser.parse_args())

verbose = args['verbose']

if verbose:
    print(f'args={pformat(args)}', file=sys.stderr)

if not args['pattern_and_files']:
    print(usage)
    print
    print(examples)
    sys.exit(1)
    # usage("missing positional args",
    #       caller=a.get('caller', None),
    #       all_cfg=all_cfg)


opt = {}

# pop out the first positional arg, which is the pattern
first_pattern = args['pattern_and_files'].pop(0)

if verbose:
    print(f'first_pattern={first_pattern}', file=sys.stderr)

patterns = [first_pattern]
if args['MatchPatterns']:
    patterns.extend(args['MatchPatterns'])

if args['exclusive']:
    opt['ExcludePatterns'] = patterns
else:
    opt['MatchPatterns'] = patterns

# files = glob(args['file'])
files = []
if args['pattern_and_files']:
    files.extend(args['pattern_and_files'])
else:
    files.append('-')

opt['print_output'] = True
opt['verbose'] = args['verbose']
opt['CaseInsensitive'] = args['CaseInsensitive']
opt['Recursive'] = args['Recursive']
opt['FileNameOnly'] = args['FileNameOnly']

if verbose:
    print(f'opt={pformat(opt)}', file=sys.stderr)
    print(f'files={pformat(files)}', file=sys.stderr)

tpgrep(files, **opt)
