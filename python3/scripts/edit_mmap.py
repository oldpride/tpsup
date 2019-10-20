#!/usr/bin/env python3

import os
import sys
import argparse
import textwrap
from pprint import pprint, pformat
import mmap


def main():
    prog = os.path.basename(sys.argv[0])

    usage = textwrap.dedent("""
        use mmap to edit a file.
        To create a binary test file, use "xxd".
        echo 0000 0101 6865 6c6c 6f20 776f 726c 640a 000 |xxd -r >edit_mmap.bin
        note: the first 0000 is the starting address, not the data.
        To display: xxd edit_mmap.bin
        """)

    examples = textwrap.dedent(f"""
        examples:
        {prog} "hello world" "hi space" edit_mmap.bin
        """)

    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description=usage,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples)

    parser.add_argument(
        'old_string', default=None, action='store', help='old_string to be replaced')

    parser.add_argument(
        'new_string', default=None, action='store', help='new_string to replace with')

    parser.add_argument(
        'filename', default=None, action='store', help='filename')

    parser.add_argument(
        '-v', '--verbose', default=0, action="count",
        help='verbose level: -v, -vv, -vvv')

    args = vars(parser.parse_args())

    if args['verbose'] > 0:
        print(f'args =\n{pformat(args)}')

    sys.exit(download_fix(**args))


def edit_mmap(**opt):
    version = opt['version']
    _dir = opt['dir']

    old_string = opt['old_string']
    new_string = opt['new_string']
    filename = opt['filename']

    # https://docs.python.org/2/library/mmap.html
    with open(filename, "r+b") as f:
        # memory-map the file, size 0 means whole file
        mm = mmap.mmap(f.fileno(), 0)
        mm[:] = re.sub('')
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
