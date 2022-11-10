#!/usr/bin/env python

import os
import sys
import argparse
import textwrap
from pprint import pformat

# choose among urllib, urllib2, urllib3, requests
# https://stackoverflow.com/questions/2018026/what-are-the-differences-between-the-urllib-urllib2-urllib3-and-requests-modul
import requests

prog = os.path.basename(sys.argv[0])

usage = textwrap.dedent(f"""
usage:
    {prog} url
  
    test ssl

example:

    {prog} https://equilend.com
    """)

examples = textwrap.dedent(f"""

{prog} https://equilend.com

    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    'url', default=None,
    help='url')

parser.add_argument(
    '-v', '--verbose', action="store_true",
    help='print some detail')

args = vars(parser.parse_args())

verbose = args['verbose']
if verbose:
    sys.stderr.write(f"args =\n{pformat(args)}\n")

url = args['url']

headers = {
    'User-Agent': 'Mozilla/5.0',
    'From': 'youremail@domain.com'  # This is another valid field
}

resp = requests.get(url)

if verbose:
    print(f'resp = {pformat(resp.text)}')
else:
    print(f'resp = {pformat(resp)}')


