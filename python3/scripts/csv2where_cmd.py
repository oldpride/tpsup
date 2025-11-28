'''
this script takes a CSV file as input and converts each row into a SQL where clause.
for example, a CSV file like this:
    id,name,age
    1,Alice,30
    2,Bob,25
    3,Charlie,35
will be converted to:
    (id='1' and name='Alice' and age='30') or 
    (id='2' and name='Bob' and age='25') or 
    (id='3' and name='Charlie' and age='35')
'''

import argparse
import csv
import os
import sys

prog = os.path.basename(__file__).replace('_cmd.py', '')

usage = f'''
usage:
    {prog} [options] csvfile
    
    Convert CSV file to SQL where clause.
'''
examples = f'''
examples:
    {prog} csv2where_test.csv
    {prog} -q csv2where_test.csv
    {prog} -s ';' csv2where_test.csv
'''
def csv2where(csvfile, sep=',', quotechar='"', add_quotes=True):
    where_clauses = []
    with open(csvfile, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=sep, quotechar=quotechar)
        for row in reader:
            conditions = []
            for key, value in row.items():
                if add_quotes:
                    conditions.append(f"{key}='{value}'")
                else:
                    conditions.append(f"{key}={value}")
            where_clause = '(' + ' and '.join(conditions) + ')'
            where_clauses.append(where_clause)
    return ' or \n'.join(where_clauses)
def main():
    parser = argparse.ArgumentParser(
        description=usage,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples)
    
    parser.add_argument(
        'csvfile',
        nargs='?',
        help='Input CSV file')
    parser.add_argument(
        '-s', '--sep',
        default=',',
        help='CSV separator character (default: ,)')
    parser.add_argument(
        '-q', '--quotechar',
        default='"',
        help='CSV quote character (default: ")')
    parser.add_argument(
        '--no-quotes',
        action='store_true',
        help='Do not add quotes around values in the where clause')
    args = parser.parse_args()

    if not args.csvfile:
        print(usage)
        print(examples)
        sys.exit(1)

    where_clause = csv2where(
        args.csvfile,
        sep=args.sep,
        quotechar=args.quotechar,
        add_quotes=not args.no_quotes)
    print(where_clause)
if __name__ == '__main__':
    main()
