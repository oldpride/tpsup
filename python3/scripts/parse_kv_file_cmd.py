#!/usr/bin/env python

from glob import glob
import os
import sys
import argparse
import textwrap
from pprint import pprint, pformat
from tpsup.keyvaluetools import parse_keyvalue

prog = os.path.basename(sys.argv[0]).replace('_cmd.py', '')

usage = textwrap.dedent("""
    usage:
        {prog} file
                            
    """)

examples = textwrap.dedent(f"""
    examples:
                           
        {prog}   {prog}_test.txt

    -v       verbose

    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    '-v', dest='verbose', default=0, action="count", help='verbose mode. -v, -vv, -vvv, ...')

parser.add_argument(
    'remaining_args',
    # 0 or more positional arguments. can handle intermixed options and positional args.
    nargs='*',
    help='optionally additonal files')

args = vars(parser.parse_args())

verbose = args['verbose']

if verbose:
    print(f'args={pformat(args)}', file=sys.stderr)

if not len(args['remaining_args']) == 1:
    print(usage)
    print
    print(examples)
    sys.exit(1)

opt = {}

fileName = args['remaining_args'][0]
with open(fileName, 'r') as f:
    inputString = f.read()

# print(f'inputString={inputString}')

parsed_kv = parse_keyvalue(inputString)


print(f'{pformat(parsed_kv)}')
