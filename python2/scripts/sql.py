#!/usr/bin/env python2.7

import os
import sys
import argparse
import textwrap
from pprint import pprint, pformat
from tpsup.sql import run_sql

prog = os.path.basename(sys.argv[0])

usage = textwrap.dedent("""/
    run oracle sql
    """)

examples = textwrap.dedent("""
    examples:
    sql.py ORACLE_USER@ORACLE_DB "select * from all_synonyms"
    sql.py -f ORACLE_USER@ORACLE_DB sql_test.sql
    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    'nickname', default=None, action='store', help='db nickname is defined in config file')

parser.add_argument(
    'statement', default=None, action='store',
    help='sql statement')

parser.add_argument(
    '-c', '--connfile', dest="connfile", action='store', type=str,
    help="db connection config file, default to ~/.tpsup/conn.csv")

parser.add_argument(
    '-o', '--output', dest="output", default="-", action='store', type=str, help="output, default to stdout")

parser.add_argument(
    '-f', '--sqlfile', action="store_true",
    help="sql file instead of sql statement")

parser.add_argument(
    '-v', '--verbose', action="store_true", help='print some detail')

args = vars(parser.parse_args())

if (args['verbose']):
    print >> sys.stderr, "args ="
    print >> sys.stderr, pformat(args)

nickname = args['nickname']

opt = {}

opt['nickname'] = args['nickname']

if 'connfile' in args: opt['connfile'] = args['connfile']

if 'odelimiter' in args: opt['odelimiter'] = args['odelimiter']

if 'output' in args:
    opt['output'] = args['output']

if args['sqlfile']:
    with open(args['statement'], 'r') as sqlfile:
        statement = sqlfile.read()
        sqlfile.close()
else:
    statement = args['statement']

if (args['verbose']):
    print >> sys.stderr, "opt ="
    print >> sys.stderr, pformat(opt)

run_sql(statement, **opt)
