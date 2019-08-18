#!/usr/bin/env python3

import csv
import gzip
import sys
import pprint

if len(sys.argv) != 2:
    print(f"""
usage: 
    {sys.argv[0]} filename
    {sys.argv[0]} /home/tian/github/tpsup/python3/lib/tpsup/csvwrapper_test.csv
    {sys.argv[0]} /home/tian/github/tpsup/python3/lib/tpsup/csvwrapper_test.csv.gz
    cat /home/tian/github/tpsup/python3/lib/tpsup/csvwrapper_test.csv | {sys.argv[0]} -
""")
    sys.exit(1)

filename = str(sys.argv[1])

if filename == '-':
    fh = sys.stdin
elif filename.endswith('.gz'):
    fh = gzip.open(filename, 'rt', encoding='utf-8', newline='')
else:
    fh = open(filename, 'r', encoding='utf-8', newline='')

csv_reader = csv.DictReader(fh)

for row in csv_reader:
    pprint.pprint(row)

