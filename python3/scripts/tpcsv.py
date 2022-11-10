#!/usr/bin/env python

import argparse
import sys
import textwrap
from pprint import pformat
# print(sys.path)
import tpsup.csvtools

usage = textwrap.dedent("""
    parse csv file like perl-version tpcsv
    """)

examples = textwrap.dedent(""" 
examples:
    tpcsv.py                 tpcsv_py_test.csv
    tpcsv.py -f number,alpha tpcsv_py_test.csv
    
    tpcsv.py      -od '|' tpcsv_py_test.csv
    tpcsv.py -d , -od '|' tpcsv_py_test.csv
    
    tpcsv.py -mp 'c,2' tpcsv_py_test.csv
    tpcsv.py -xp 'c,2' tpcsv_py_test.csv
    
    tpcsv.py -me "r['alpha'] is 'c'" tpcsv_py_test.csv
    tpcsv.py -xe "r['alpha'] is 'c'" tpcsv_py_test.csv
    
    tpcsv.py -me "re.search('c', r['alpha'])" tpcsv_py_test.csv
    
    # for raw pattern, use r in front of the pattern, compare the following two
    tpcsv.py -me "re.search(r'\\\\\\\\w', r['alpha'])" tpcsv_py_test.csv
    tpcsv.py -me "re.search( '\\\\\\\\w', r['alpha'])" tpcsv_py_test.csv
    
    # can also use different quote combination, to save some \\
    tpcsv.py -me 're.search(r"\\\\w", r["alpha"])' tpcsv_py_test.csv
    tpcsv.py -me 're.search( "\\\\w", r["alpha"])' tpcsv_py_test.csv
    
    # use temporary expression. the first doesn't print; the second one does
    tpcsv.py -te "a2=r['alpha']+'z'" -te n2="int(r['number'])+100"              tpcsv_py_test.csv
    tpcsv.py -te "a2=r['alpha']+'z'" -te n2="int(r['number'])+100" -f number,n2 tpcsv_py_test.csv
    
    tpcsv.py -o /tmp/junk.csv tpcsv_py_test.csv; cat /tmp/junk.csv
    cat tpcsv_py_test.csv | tpcsv.py -
    
    tpcsv.py                         tpcsv_py_test_missing.csv
    tpcsv.py -f number,alpha         tpcsv_py_test_missing.csv
    tpcsv.py -me "r['alpha'] is 'c'" tpcsv_py_test_missing.csv
    
    tpcsv.py         tpcsv_py_test_skip_header.csv
    tpcsv.py -skip 2 tpcsv_py_test_skip_header.csv
    
    # test empty file
    tpcsv.py tpcsv_py_test_empty.csv
    
    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    'filename', default=None,
    help='input csv file')

parser.add_argument(
    '-mp', '--MatchPatterns', action='append',
    help="match pattern, eg, 'c,2', can use multiple times, AND logic, like a grep pipe")

parser.add_argument(
    '-xp', '--ExcludePatterns', action='append',
    help="exclude pattern, eg, 'c,2', can use multiple times, AND logic, like a grep -v")

parser.add_argument(
    '-me', '--MatchExps', action='append',
    help="match expression, eg, r['alpha'] is 'c', can use multiple times, AND logic, like a grep pipe")

parser.add_argument(
    '-xe', '--ExcludeExps', action='append',
    help="exclude expression, eg, r['alpha'] is 'c', can use multiple times, AND logic, like a grep -v pipe")

parser.add_argument(
    '-te', '--TempExps', action='append',
    help="temp expression, eg, a2=r['alpha']+'z', n2=r['number']+100, can use multiple times. will not be printed.")

parser.add_argument(
    '-ee', '--ExportExps', action='append',
    help="export expression, eg, a2=r['alpha']+'z', n2=r['number']+100, can use multiple times. will be printed")

parser.add_argument(
    '-f', '--fields', dest='SelectFields', action='store',
    help="select columns (including temp columns) to output, eg, -f alpha")

parser.add_argument(
    '-v', '--verbose', default=0, action="count",
    help='verbose level: -v, -vv, -vvv')

parser.add_argument(
    '-o', '-output', dest="Output", default='-', action='store',
    help="output file, default to '-', STDOUT")

parser.add_argument(
    '-d', '-delimiter', dest="delimiter", default=',', action='store',
    help="input delimiter, default to ','")

parser.add_argument(
    '-od', '-odelimiter', dest="OutDelimiter", default=None, action='store',
    help="output delimiter, default to input delimiter, or then ','")

parser.add_argument(
    '-skip', dest="skip", default=0, action='store', type=int,
    help="skip these number of lines before header, default to 0")

args = vars(parser.parse_args())

if args['verbose'] >= 1:
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

#query_csv(**args);

with tpsup.csvtools.QueryCsv(
              **args) as qc:
    args.pop('filename')
    qc.output(filename=args['Output'], **args)
