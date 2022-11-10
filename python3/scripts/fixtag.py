#!/usr/bin/env python

import argparse
import io
import os
import sys
import textwrap
from pprint import pformat

from tpsup.fixtools import dump_fix_message

prog = os.path.basename(sys.argv[0])

usage = textwrap.dedent("""
    translate fix tag into field
    """)

examples = textwrap.dedent(f""" 
examples:

   {prog} fixtag_test.txt

   {prog} -t 35,49,50,56,57,115 fixtag_test.txt

   - test the string on command line
   {prog} -s 35=AB,54=B,555=2
   {prog} -s 35=AB,54=B
   {prog} -s 35=D

   - to dump a nested fix message and use stdin
   head -n 1 fixlog2csv_test_multileg.txt | {prog} -

   - to overwrite standard tags, pay attention to tag 35 and 54 in the following outputs
   {prog} -t 35,54                           fixtag_test.txt
   {prog} -t 35,54 -dict fixtag_test_dict.py fixtag_test.txt

    """)

parser = argparse.ArgumentParser(
    description=usage,
    prog=sys.argv[0],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    'input', default=None,
    help='input fix file')

parser.add_argument(
    '-t', '--tags', action='store', default=None,
    help="select to display only these tags: eg, 35,54")

parser.add_argument(
    '-v', '--verbose', default=0, action="count",
    help='verbose level: -v, -vv, -vvv')

parser.add_argument(
    '-s', '--StringInput', action="store_true",
    help='input is a string on command line')

parser.add_argument(
    '-d', '-delimiter', dest="FixDelimiter", default=None, action='store',
    help="input FIX delimiter, default to ','")

parser.add_argument(
    '-dict', dest="FixDict", default=None, action='store',
    help="extra dictionary to resolve fix tags and values")

args = vars(parser.parse_args())

if args['verbose']:
    sys.stderr.write("args =\n")
    sys.stderr.write(pformat(args) + "\n")

# https://pythontips.com/2013/08/04/args-and-kwargs-in-python-explained/
# *args and **kwargs allow you to pass a variable number of arguments to
# a function. What does variable mean here is that you do not know before
# hand that how many arguments can be passed to your function by the user
# so in this case you use these two keywords.
# *args is used to send a non-keyworded variable length argument list to
# the function.
# **kwargs allows you to pass keyworded variable length of arguments to
# a function. You should use **kwargs if you want to handle named arguments
# in a function.

infile = args.get('input')

if args.get('StringInput'):
    fh = io.BytesIO(infile.encode('utf-8'))
elif infile == '-':
    fh = sys.stdin.buffer
else:
    fh = open(infile, 'rb')

for line in fh:
    dump_fix_message(line, **args)
