#!/usr/bin/env python

import os
import sys
import argparse
import textwrap
from pprint import pprint, pformat
import mmap


def main():
    prog = os.path.basename(sys.argv[0])

    usage = textwrap.dedent("""
use mmap to edit a file. Key point: keep the file size the same.   
        """)

    examples = textwrap.dedent(f"""
examples:
    create a test binary file, use "xxd":
        echo 0000 0101 6865 6c6c 6f20 776f 726c 640a 000 |xxd -r >edit_mmap1.bin   
    note: the first 0000 is the starting address, not the data.
        
    To display
        xxd edit_mmap1.bin

    Save a copy, so that we can compare later
        cp edit_mmap1.bin edit_mmap2.bin

    Replace long string with short string
        {prog} "hello world" "hi space" edit_mmap1.bin
        diff_binary edit_mmap1.bin edit_mmap2.bin

    Replace short string with long string    
        {prog} "hi space" "hello world" edit_mmap1.bin
        diff_binary edit_mmap1.bin edit_mmap2.bin 
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

    edit_mmap(**args)
    sys.exit(0)


def edit_mmap(**opt):
    old_string = opt['old_string'].encode('utf-8')
    new_string = opt['new_string'].encode('utf-8')
    filename = opt['filename']

    # https://docs.python.org/2/library/mmap.html
    with open(filename, "r+b") as f:
        # memory-map the file, size 0 means whole file
        mm = mmap.mmap(f.fileno(), 0)
        index = mm.find(old_string)
        if index != -1:
            old_len = len(old_string)
            new_len = len(new_string)
            if new_len > old_len:
                sys.stderr.write(f'Warning: new string (len={new_len}) is longer than old string (len={old_len}). '
                                 f'Please check result\n')
            mm[index:index+new_len] = new_string
            if new_len < old_len:
                mm[index+new_len:index+old_len] = bytearray([0]*(old_len-new_len))
            else:
                mm[index+new_len] = 0
        else:
            sys.stderr.write(f'cannot find old string in {filename}\n')
        mm.close()


if __name__ == '__main__':
    main()
