#!/usr/bin/env python

import os
import sys
import argparse
import textwrap
from pprint import pprint, pformat
from tpsup.sqltools import run_sql

prog = os.path.basename(sys.argv[0])

usage = textwrap.dedent("""
    run oracle sql
    run ms sql (odbc) sql
    run mysql sql
    """)

examples = textwrap.dedent(f"""
    examples:
    {prog} -maxout 5 ora_user@ora_db "select * from all_synonyms"

    {prog} -maxout 5 sql_user@sql_db "select * from information.schema.tables where table_type = 'BASE TABLE'"

    - mysql 
    {prog} tian@tiandb "SHOW TABLES"

    {prog} -f ORACLE_USER@ORACLE_DB tpsql_test.sql
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
    '-o', '--output', dest="SqlOutput", default="-", action='store', type=str, help="output, default to stdout")

parser.add_argument(
    '-d', '--delimiter', dest="SqlDelimiter", default=",", action='store', type=str, help="output delimiter")

parser.add_argument(
    '-f', '--sqlfile', action="store_true",
    help="sql file instead of sql statement")

parser.add_argument(
    '-noheader', dest='PrintNoHeader', action="store_true",
    help="not to print header line")

parser.add_argument(
    '-maxout', dest='maxout', default=-1, type=int, action="store",
    help="max rows of output")

parser.add_argument(
    '-v', '--verbose', default=0, action="count",
    help='verbose level: -v, -vv, -vvv')

args = vars(parser.parse_args())

if args['sqlfile']:
    with open(args['statement'], 'r') as sqlfile:
        statement = sqlfile.read()
else:
    statement = args['statement']

if args['verbose'] > 0:
    print(f'args =\n{pformat(args)}')

sys.exit(run_sql([statement], **args))



