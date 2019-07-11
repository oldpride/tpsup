#!/usr/bin/env python2.7

# PYTHONPATH=:${TPSUP}/tpsup/python2.7/1ib
from tpsup.util import tpfind

import argparse
import sys
import textwrap
from pprint import pprint,pformat

usage = textwrap.dedent(""""\
    a better 'find' command
    """)

examples = textwrap.dedent(""" 
examples:
    # print the dir tree
    tpfind.py -maxdepth 2 -trace ~/tpsup

    # use handlers
    tpfind.py -maxdepth 1 -trace -he 're.search("tpstamp", r["path"])' \\
    -ha 'ls(r)' ~/tpsup

    tpfind.py -maxdepth 1 -trace -he 're.search("tpstamp", r["path"])' \\
    -ha 'os.system("ls -1 " + r["path"])' -he 're.search("proj", r["path"])' \\
    -ha 'os.system("ls -1 " + r["path"])' ~/tpsup

    # flow control
    tpfind.py -trace -fe 're.search("autopath|scripts|proj|lib|i86pc|Linux", r["path"])'\\
    -fd 'prune' ~/tpsup

    tpfind.py -trace -fe 're.search("autopath", r["path"])' -fd 'exit1' ~/tpsup; echo $?

    # use handlers as a filter
    tpfind.py -he 're.search("scripts", r["path"])' -ha 'ls(r)' ~/tpsup

    # owner
    tpfind.py -he 'r["owner"] != "tian"' -ha 'ls(r)' ~/tpsup

    # mtime/now. eg, file changed yesterday, one day is 86400 seconds
    tpfind.py -he 'r["mtime"]<now-86400 and r["mtime"]>now-2*86400' -ha 'ls(r)' ~/tpsup

    # mode, find file group/other-writable
    tpfind.py -he 'r["type"] != "link" and r["mode"] & 0022' -ha 'ls(r)' ~/tpsup

    # mode, find dir not executable or readable
    tpfind.py -he 'r["type"] == "dir" and (r["mode"] & 0555) != 0555' -ha 'ls(r)' ~/tpsup

    # size, eg, file is bigger than 100K
    tpfind.py -he 'r["size"] >100000' -ha 'ls(r)' -/tpsup

    # ifh is the open file handler, the following command find all bash scripts
    tpfind.py -he 'r["type"] == "file"' \\
    -ha 'if re.search(r"^#!.*/bash\\b",ifh.readline()): ls(r)' ~/tpsup
    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples);

parser.add_argument(
    'paths', default=None, action='append',
    help='input path')

parser.add_argument(
    '-he', '--HandleExps', action='append',
    help="Handle match expression, paired with -ha/--HandleActs")

parser.add_argument(
    '-ha', '--HandleActs', action='append',
    help="Handle action after matching, paired with -he/--HandleExps")

parser.add_argument(
    '-fe', '--FlowExps', action='append',
    help="Flow control match expression, paired with -fd/--FlowDirs")

parser.add_argument(
    '-fd', '--FlowDirs', action='append',
    help="Flow control direction after matching, paired with -fd/--FlowExps")

parser.add_argument(
    '-maxdepth', dest="maxdepth", default=100, action='store', type=int,
    help="max depth, default 100. the path specified by command line has depth 0")

parser.add_argument(
    '-trace', '--Trace', action='store_true',
    help="print the paths that the script has browsed")

parser.add_argument(
    '-v', '--verbose', action="store_true",
    help='print some detail')

args = vars(parser.parse_args())

if (args['verbose']):
    print >> sys.stderr, "args ="
    print >> sys.stderr, pformat(args)

# https://pythontips.com/2013/08/04/args-and-kwargs-in-python-explained/
# *args and **kwargs allow you to pass a variable number of arguments to a function.
# What does variable mean here is that you do not know before hand that how many
# arguments can be passed to your function by the user so in this case you use these
# two keywords.
# *args is used to send a non-keyworded variable length argument list to the function.
# **kwargs allows you to pass keyworded variable length of arguments to a function.
# You should use **kwargs if you want to handle named arguments in a function.
tpfind(**args);
