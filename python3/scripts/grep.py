#!/usr/bin/env python

import os
import sys
import argparse
import textwrap
from pprint import pprint, pformat
from tpsup.greptools import grep

prog = os.path.basename(sys.argv[0])

usage = textwrap.dedent("""
    grep command in python, so that we can run it on windows.
    """)

examples = textwrap.dedent(f"""
    examples:
    {prog} -maxout 5 ora_user@ora_db "select * from all_synonyms"

    {prog} -maxout 5 sql_user@sql_db "select * from information.schema.tables where table_type = 'BASE TABLE'"

    - mysql 
    {prog} tian@tiandb "SHOW TABLES"

    {prog} -f ORACLE_USER@ORACLE_DB tpsql_test.sql

    # prepare ms sql database for testing
    {prog} -f tptest@tpdbmssql tptrace_test_db.sql

    # run ms sql sql
    {prog} tptest@tpdbmssql 'select name from sys.tables'
    {prog} tptest@tpdbmssql 'select @@version'
    {prog} tptest@tpdbmssql 'exec sp_who' # shows which user/database
    {prog} -render tptest@tpdbmssql 'select * from orders' # print grid
    {prog} -PrintNoHeader tptest@tpdbmssql 'select * from orders' # print no header
    {prog} -maxout 2 tptest@tpdbmssql 'select * from orders' # print 2 rows
    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    'nickname', default=None, action='store', help='db nickname is defined in config file')

parser.add_argument(
    'sql', default=None, action='store',
    help='sql or sql file')

parser.add_argument(
    '-c', '--connfile', dest="connfile", action='store', type=str,
    help="db connection config file, default to ~/.tpsup/conn.csv")

parser.add_argument(
    '-o', '--output', dest="SqlOutput", default="-", action='store', type=str, help="output, default to stdout")

parser.add_argument(
    '-d', '--delimiter', dest="SqlDelimiter", default=",", action='store', type=str, help="output delimiter")

parser.add_argument(
    '-f', dest='is_sqlfile', action="store_true",
    default=False, help='sql is a file')

parser.add_argument(
    '-noheader', dest='PrintNoHeader', action="store_true",
    help="not to print header line")

parser.add_argument(
    '-render', dest='render', action="store_true",
    help="render output in grid")

parser.add_argument(
    '-maxout', dest='maxout', default=-1, type=int, action="store",
    help="max rows of output")

parser.add_argument(
    '-v', '--verbose', default=0, action="count",
    help='verbose level: -v, -vv, -vvv')

args = vars(parser.parse_args())


if args['is_sqlfile']:
    with open(args['sql'], 'r') as sqlfile:
        sql = sqlfile.read()
else:
    sql = args['sql']

# remove sql from args to avoid this error:
# TypeError: run_sql() got multiple values for argument 'sql'
args.pop('sql')

if args['render']:
    args['RenderOutput'] = 1
    if args['PrintNoHeader']:
        args['RenderHeader'] = 0
    else:
        args['RenderHeader'] = 1

if args['verbose'] > 0:
    print(f'args =\n{pformat(args)}')
    print(f'sql =\n{sql}')

run_sql(sql, **args)
# sys.exit(run_sql(sql, **args))
