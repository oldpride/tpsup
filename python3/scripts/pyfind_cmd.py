#!/usr/bin/env python

from glob import glob
import os
import sys
import argparse
import textwrap
from pprint import pprint, pformat
from tpsup.tpfile import tpfind

prog = os.path.basename(sys.argv[0]).replace('_cmd.py', '')

usage = textwrap.dedent("""
    usage:
        {prog} pattern file1 file2 ...
                            
        'grep' command implemented in python, so that we can run it on windows.
    """)

examples = textwrap.dedent(f"""
    examples:
                           
        {prog}  [options]    path

        -he -HandleExp   Handle expression, can specify multiple times
        -ha -HanderAct   Handle action, can specify multiple times
        -fe -FlowExp     flow expression, can specify multiple times
        -fa -FlowAct     flow action, can specify multiple times
        -print           print path
        -ls              print like 'ls -l'
        -dump            print out detail of the path

        {prog} .

        {prog} -fe 'not r["short"].endswith("profile.d")' -fa prune $TPSUP
        {prog} -fe 'r["size"] > 5000'                        -fd exit $TPSUP
        {prog} -fe 'r["size"] > 5000 and r["type"] != "dir"' -fd exit $TPSUP

    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    'paths', action="append", help='paths')

parser.add_argument(
    '-he', '-HandleExp', dest='HandleExps', action="append", default=[],
    help='Handle Expression - Python expression')

parser.add_argument(
    '-ha', '-HandleAct', dest='HandleActs', action="append", default=[],
    help='Handle Action - Python code')

parser.add_argument(
    '-fe', '-FlowExp', dest='FlowExps', action="append", default=[],
    help='Flow Expression - Python expression')

parser.add_argument(
    '-fd', '-FlowDir', dest='FlowDirs', action="append", default=[],
    help='Flow Directives, eg, prune, exit, ...')

parser.add_argument(
    '-print', dest='find_dump', action="store_true",
    help='print path')

parser.add_argument(
    '-ls', dest='find_ls', action="store_true",
    help='print like ls -l')

parser.add_argument(
    '-dump', dest='find_dump', action="store_true",
    help='print out detail of the path')

parser.add_argument(
    # https://stackoverflow.com/questions/15583870
    # "argparse.REMAINDER" tells the argparse module to take the rest of the arguments in args,
    # when it finds the first argument it cannot match to the rest.
    'remainingArgs', nargs=argparse.REMAINDER,
    # this may not be desirable.
    # but the parser cannot handle intermixed options and positional args.
    help='optionally additonal paths')

parser.add_argument(
    '-d', dest='verbose', default=0, action="count",
    help='verbose mode. -d, -dd, -ddd, ...')

args = vars(parser.parse_args())

verbose = args['verbose']

if verbose:
    print(f'args={pformat(args)}', file=sys.stderr)


if args['remainingArgs']:
    args['paths'].extend(args['remainingArgs'])

tpfind(**args)