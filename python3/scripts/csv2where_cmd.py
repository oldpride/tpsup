'''
this script takes a CSV file as input and converts each row into a SQL where clause.
for example, a CSV file like this:
    t.id(number),t.name,t.age(number)
    1,Alice,30
    2,Bob,25
    3,Charlie,35
will be converted to:
    (t.id=1 and t.name='Alice' and t.age=30) or
    (t.id=2 and t.name='Bob' and t.age=25) or
    (t.id=3 and t.name='Charlie' and t.age=35)

'''

import argparse
import csv
import os
import re
import sys

prog = os.path.basename(__file__).replace('_cmd.py', '')

usage = f'''
this script takes a CSV file as input and converts each row into a SQL where clause.
for example, a CSV file like this:
    t.id(number),t.name,t.age(number),t.score(abs)
    1,Alice,30,"(100,111)"
    2,Bob,25,222
    3,Charlie,35,333.5
will be converted to:
    (t.id=1 and t.name='Alice' and t.age=30 and abs(t.score)=100111.0) or
    (t.id=2 and t.name='Bob' and t.age=25 and abs(t.score)=222.0) or
    (t.id=3 and t.name='Charlie' and t.age=35 and abs(t.score)=333.5)
usage:
    {prog} [options] csvfile

    -debug    Enable debug mode

    Convert CSV file to SQL where clause.
'''
examples = f'''
examples:
    {prog} csv2where_test.csv
    {prog} -q csv2where_test.csv
    {prog} -s ';' csv2where_test.csv
'''
def csv2where(csvfile, sep=',', quotechar='"', add_quotes=True, debug=False):
    where_clauses = []
    # remove DOS line ending if any
    with open(csvfile, 'r', newline='', encoding='utf-8') as f:
    # with open(csvfile, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=sep, quotechar=quotechar)
        for row in reader:
            conditions = []
            for key, value in row.items():
                key = key.strip()
                value = value.strip()
                if debug:
                    print(f"key: '{key}', value: '{value}'")

                add_quotes = True

                # is key is t.id(number), convert key to t.id, and don't add quotes around value
                if m := re.match(r'^([a-zA-Z_][a-zA-Z0-9_.]*)\s*\((.*)\)$', key):
                    key = m.group(1)
                    type_hint = m.group(2)

                    if type_hint:
                        if re.search(r'number|int|float|abs', type_hint, re.IGNORECASE):
                            add_quotes = False

                            # remove ',' from value, eg, '1,234' to '1234'
                            value = value.replace(',', '')

                            # convert value (123) to -123
                            if m2 :=re.match(r'^\((\d+(\.\d+)?)\)$', value):
                                value = '-' + m2.group(1)
                    
                            if re.search(r'abs', type_hint, re.IGNORECASE):
                                key = f"abs({key})"
                                value = abs(float(value))

                if add_quotes:
                    conditions.append(f"{key}='{value}'")
                else:
                    conditions.append(f"{key}={value}")
            where_clause = '( ' + ' and '.join(conditions) + ' )'
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
        '-debug',
        action='store_true',
        help='Enable debug mode')
    args = parser.parse_args()

    if not args.csvfile:
        print(usage)
        print(examples)
        sys.exit(1)

    where_clause = csv2where(
        args.csvfile,
        sep=args.sep,
        debug=args.debug
        )
    print(where_clause)
if __name__ == '__main__':
    main()
