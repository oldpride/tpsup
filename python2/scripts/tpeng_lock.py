#!/usr/bin/env python2.7

from tpsup.util import tpeng_lock, tpeng_unlock
import os
import sys
import re
import argparse
import textwrap
from pprint import pprint, pformat

usage = textwrap.dedent("""\
    encode a string
    decode a string
    """)

examples = textwrap.dedent("""
    examples:
    tpeng_lock.py HelloWorld
    tpeng_unlock.py %09%06%0F%05%00%14%00%1C%0A%11
    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage, formatter_class=argparse.RawDescriptionHelpFormatter, epilog=examples)

parser.add_argument(
    'string', default=None, action='store',
    help='text string')

parser.add_argument(
    '-v', '--verbose', action="store_true",
    help='print some detail')

args = vars(parser.parse_args())

if (args['verbose']):
    print >> sys.stderr, "args ="
    print >> sys.stderr, pformat(args)

basename = os.path.basename(sys.argv[0])

if re.search("tpeng_unlock", basename):
    print tpeng_unlock(args['string'], None)
elif re.search("tpeng_lock", basename):
    print tpeng_lock(args['string'], None)
else:
    print >> sys.stderr, "cannot figure out encode or decode from basename: " + basename
    sys.exit(1)
