#!/usr/bin/env python

from glob import glob
import os
import sys
import argparse
import textwrap
from pprint import pprint, pformat
from tpsup.filetools import tpfind

prog = os.path.basename(sys.argv[0]).replace('_cmd.py', '')

usage = textwrap.dedent("""
    usage:
        {prog} pattern file1 file2 ...
                            
        'grep' command implemented in python, so that we can run it on windows.
    """)

examples = textwrap.dedent(f"""
    examples:
                           
        {prog}  [options]    path

        pyfind vs tpfind.py
            tpfind.py is mainly tested on linux.
            pyfind tested on both linux and windows, and is module based.
            pyfind is the future.

        -m exp                 Match expression, can specify multiple times.  
        -he -HandleExp exp     Handle expression, can specify multiple times
        -ha -HanderAct code    Handle action, can specify multiple times
        -fe -FlowExp exp       flow expression, can specify multiple times
        -fd -FlowDir dir       flow directive, can specify multiple times
        -print                 print path
        -ls                    print like 'ls -l'
        -dump                  print out detail of the path
        -maxdepth  int         max depth to search. 0 means given path only.
        -maxcount  int         max count to search

        # print the dir tree
        {prog} -maxdepth 0 $TPSUP
        {prog} -maxdepth 1 $TPSUP
        {prog} -maxdepth 1 $TPSUP -ls
        {prog} -maxdepth 1 $TPSUP -dump

        # filter files
        {prog} -maxcount 5 -m 'r["path"].endswith(".py")' $TPSUP
        {prog} -maxcount 5 -m 'r["size"] > 50000 and r["type"] != "dir"' $TPSUP -ls

        # flow control
        {prog} -fe 'r["short"] in ["scripts", "lib", "python3", "bat"]' -fd prune $TPSUP
        {prog} -fe 'r["short"] in ["scripts", "lib", "python3", "bat"]' -fd exit  $TPSUP

        # use handlers, note: be careful with the using of quotes. i used str() here instead of f"..."
        {prog} -maxcount 5 -he '"python" in r["path"]' -ha 'os.system("ls -ld " + str(r["path"]))' $TPSUP

        # mtime/now. eg, file changed yesterday, one day is 86400 seconds
        {prog} -maxcount 5 -m 'r["mtime"]<r["now"]-86400 and r["mtime"]>r["now"]-(2*86400)' -ls $TPSUP

        # mode, eg, file is writable, 0o222 is octal. 
        # use '%' formatter instead of f"..." to reduce layer of quotes
        {prog} -maxcount 5 -he 'r["mode"] & 0o222' -ha 'print("mode=%o file=%s" % (r["mode"], r["path"]))' $TPSUP

        # getline() function
        # find script that doesn't have 755 mode
        {prog} -maxcount 5 -m "r['type'] == 'file' and (r['mode']&0o755) !=0o755 and r['size']>0 and getline().startswith('#!')" $TPSUP
                
    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    '-m', dest='MatchExps', action="append", default=[],
    help='Match Expression - Python expression')

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
    '-maxdepth', dest='MaxDepth', type=int, default=None,
    help='max depth to search')

parser.add_argument(
    '-maxcount', dest='MaxCount', type=int, default=None,
    help='max count to search')

parser.add_argument(
    'paths',  # this is the remaining args
    nargs='*',  # 0 or more positional arguments.
    help='optionally additonal paths')

parser.add_argument(
    '-d', dest='verbose', default=0, action="count",
    help='verbose mode. -d, -dd, -ddd, ...')

args = vars(parser.parse_args())

verbose = args['verbose']

if verbose:
    print(f'args={pformat(args)}', file=sys.stderr)


if not args['paths']:
    print('missing path', file=sys.stderr)
    print(usage)
    print(examples)
    sys.exit(1)

tpfind(**args)
