#!/usr/bin/env python3

import argparse
import sys
import textwrap
from pprint import pprint, pformat

usage = textwrap.dedent("""\
parse csv file like perl-version tpcsv
 """)
examples = textwrap.dedent("""
examples:
    unique.py	  a b c d e a b c
    unique.py -d, a,b,c,d,e,a,b,c
    
 """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples);

parser.add_argument(
    '-d', '-delimiter', dest="delimiter", default=None, action='store',
    help="delimiter. default to None")

parser.add_argument(
    dest="string", nargs='*',
    help="remote command")
parser.add_argument(
    '-v', '--verbose', action="store_true",
    help='print some detail')
args = vars(parser.parse_args())

if (args['verbose']):
    print >> sys.stderr, "args	="
    print >> sys.stderr, pformat(args)

a = args['string']

delimiter = args['delimiter']

if (args['verbose']):
    print >> sys.stderr, pformat(a)

def dedupe(strings):
    seen = set()
    for s in strings:
        if (delimiter):
            items = s.split(delimiter)
        else:
            items = [s]
        for item in items:
            if item not in seen:
                yield item
                seen.add(item)
# The 'yield' statement suspends function's execution and sends a value back to
# caller, but retains enough state to enable function to resume where it is
# left off. When resumed, the function continues execution immediately after
# the last yield run. This allows its code to produce a series )of values over
# time, rather them computing them at once and sending them back like a list.

# 'Return' statement sends a specified value back to its caller whereas Yield can produce
# a sequence of values. We should use yield when we want to iterate over a
# sequence, but don't want to store the entire sequence in memory.

# To master yield, you must understand that when you call the function, the
# code you have written in the function body does not run. The function only
# returns the generator object, this is a bit tricky

# Then, your code will be run each time the for uses the generator.
if (delimiter):
    print( delimiter.join(list(dedupe(a))) )
else:
    print( " ".join(list(dedupe(a))) )
