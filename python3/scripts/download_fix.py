#!/usr/bin/env python

import os
import sys
import argparse
import textwrap
from pprint import pprint, pformat

import requests
import urllib.request
import time
from bs4 import BeautifulSoup


def main():
    prog = os.path.basename(sys.argv[0])

    usage = textwrap.dedent("""
        download fix tag definitions from https://www.onixs.biz/fix-dictionary/4.2/fields_by_tag.html
        """)

    examples = textwrap.dedent(f"""
        examples:
        {prog} version output_dir
        {prog} 4.4 ~/data/fix/4.4
        """)

    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description=usage,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples)

    parser.add_argument(
        'version', default=None, action='store', help='fix protocol version')

    parser.add_argument(
        'dir', default=None, action='store',
        help='output dir')

    parser.add_argument(
        '-v', '--verbose', default=0, action="count",
        help='verbose level: -v, -vv, -vvv')

    args = vars(parser.parse_args())

    if args['verbose'] > 0:
        print(f'args =\n{pformat(args)}')

    sys.exit(download_fix(**args))


def download_fix(**opt):
    version = opt['version']
    _dir = opt['dir']

    if not os.path.exists(_dir):
        os.makedirs(_dir)

    # https://towardsdatascience.com/how-to-web-scrape-with-python-in-4-minutes-bc49186a8460
    url = f'https://www.onixs.biz/fix-dictionary/{version}/fields_by_tag.html'

    # Connect to the URL
    response = requests.get(url)

    # Parse HTML and save to BeautifulSoup object¶
    soup = BeautifulSoup(response.text, "html.parser")

    # <p; align = "center" class ="listLinks" > < a href="tagNum_1.html" > 1 < / a > & nbsp; | < a
    # href="tagNum_2.html" > 2 < / a > & nbsp; | < a href="tagNum_3.html" >

    seen_href = set()
    download_count = 0
    for a in soup.findAll('a'):
        href = a['href']
        if href.startswith("tagNum_"):
            if href in seen_href:
                continue
            seen_href.add(href)

            local_file = f'{_dir}/{href}'

            break_time = 10

            if os.path.exists(local_file):
                size = os.stat(local_file).st_size
                if size > 10000:
                    print(f'{href} is already downloaded and have a decent size {size} bytes')
                    continue
                else:
                    print(f'{href} is already downloaded and but size is only {size} bytes, try to download again')

            download_url = f'https://www.onixs.biz/fix-dictionary/{version}/{href}'
            print(f'downloading {download_url} to {local_file}')
            urllib.request.urlretrieve(download_url, local_file)

            if download_count > 0 and download_count % break_time == 0:
                time.sleep(2)  # pause the code for a sec so that they won't complain us spamming
            else:
                time.sleep(0.1)

            download_count += 1


if __name__ == '__main__':
    main()
