#!/usr/bin/env python

import os
import re
import sys
import argparse
import textwrap
from pprint import pformat

from tpsup.lock import EntryBook

prog = os.path.basename(sys.argv[0])

usage = textwrap.dedent(f"""
usage:
    {prog}                    cmd
    {prog} {prog}_switches -- cmd cmd_switches
  
    run command without explicit password

    -h        print help

    example book.csv format:
        key,user,encoded,commandpattern,setting,comment
        swagger,sys.admin,^/usr/bin/curl$|/sqlplus$,%29%06%0F%05%00,a=1;'b=john, sam',test swagger
    """)

examples = textwrap.dedent(f"""
    examples:
    
    to hide password from the following command
        echo "SHOW TABLES"|mysql -u tian -p<password> tiandb
    we do
        echo "SHOW TABLES"|{prog} -- /usr/bin/mysql -u tian -ptpentry{{tiandb}}{{decoded}} tiandb

    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    '-b', '--book', dest="book", action='store', type=str,
    help="encoded file, default to ~/.tpsup/book.csv")

parser.add_argument(
    'cmdAndArgs', default=[], nargs=argparse.REMAINDER,
    help='the real command to run, with args')

parser.add_argument(
    '-v', '--verbose', action="store_true",
    help='print some detail')

args = vars(parser.parse_args())

if args['verbose']:
    sys.stderr.write(f"args =\n{pformat(args)}\n")

cmdAndArgs = args.get('cmdAndArgs', None)
if len(cmdAndArgs) == 0:
    print("missing real command", file=sys.stderr)
    print(usage, file=sys.stderr)
    sys.exit(1)

entryBook = EntryBook(**args)

result = entryBook.run_cmd(cmdAndArgs, verbose=args['verbose'])

if args['verbose']:
    result_string = pformat(result)
    # result = CompletedProcess(args=['curl', '-u', 'sys.admin:abc123', '-v', '-w', ...]...)
    # remove the password from the output
    result_string = re.sub(r"('-u',\s+\S+?):(\S+)", r"\1:***", result_string)
    sys.stderr.write(f"result = {result_string}\n")

print(result.stdout)
print(result.stderr, file=sys.stderr)

sys.exit(result.returncode)
