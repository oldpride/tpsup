#!/usr/bin/env python
import os

import sys
import argparse
import textwrap
from pprint import pformat
import tpsup.crawlertools


prog = os.path.basename(sys.argv[0])

usage = textwrap.dedent(f"""
usage:
    {prog} img1 img2 

    
    
    -v              verbose mode. -v -v for more verbose

    

    """)

examples = textwrap.dedent(f"""
examples:
    
    {prog} 

   
    
    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

# parser.add_argument(
#     '-maxdepth', '--maxdepth', dest="maxdepth", action='store', type=int, default=3,
#     help="depth of the crawl. default is 3")

# parser.add_argument(
#     '-maxpage', '--maxpage', dest="maxpage", action='store', type=int, default=50,
#     help="max number of pages to crawl. default is 50")

# parser.add_argument(
#     '-maxsize', '--maxsize', dest="maxsize", action='store', type=int, default=10,
#     help="max size of the file to download. default is 10 (MB)")

# parser.add_argument(
#     '-xpath', '--xpath', dest="xpath", action='store', type=str, default=None,
#     help="xpath to match. default is None")

# parser.add_argument(
#     '-dd', '--download_dir', dest="download_dir", action='store', type=str, default=None,
#     help="directory for downloading")

# parser.add_argument(
#     '-pd', '--processed_dir', dest="processed_dir", action='store', type=str, default=None,
#     help="directory for processing")

parser.add_argument(
    '-v', '--verbose', dest="verbose", action='count', default=0,
    help="verbose mode. -v -v for more verbose")

# parser.add_argument(
#     '-inh', '--inhuman', dest="humanlike", action='store_false', default=True,
#     help="inhuman mode. don't add delay between requests")

# parser.add_argument(
#     '-ih', '--ignoreHttpError', dest="ignoreHttpError", action='store_true', default=False,
#     help="ignore http error. default is False")

parser.add_argument(
    'remainingArgs', default=None, nargs=argparse.REMAINDER,
    help='url and xpath')

args = vars(parser.parse_args())


if args['verbose']:
    sys.stderr.write(f"args =\n{pformat(args)}\n")

remainingArgs = args['remainingArgs']
if len(remainingArgs) != 2:
    sys.stderr.write("missing args\n")
    sys.stderr.write(usage)
    sys.stderr.write(examples)
    sys.exit(1)

f1 = remainingArgs[0]
f2 = remainingArgs[1]


# This module is used to load images
from PIL import Image
# This module contains a number of arithmetical image operations
from PIL import ImageChops

def image_diff_size(img1: Image, img2: Image):
    # first compare sizes
    width1, height1 = img1.size
    width2, height2 = img2.size

    if width1 != width2 or height1 != height2:
        print(f"dimension mismatch: ({width1}, {height1}) vs ({width2}, {height2})")
        return False
    else:
        print(f"dimension match: ({width1}, {height1}) vs ({width2}, {height2})")
        return True

def image_diff_pixel(img1: Image, img2: Image):
    # first compare sizes
    width1, height1 = img1.size
    width2, height2 = img2.size

    if not image_diff_size(img1, img2):
        return False
    
    diff = ImageChops.difference(img1, img2)
    if diff.getbbox():
        # print out the differences
        diff.show()
        print("difference found")
        return False
    else:
        diff.show()
        print("no difference")
        return True

base_image = Image.open(f1)
compare_image = Image.open(f2)
results = image_diff_pixel(base_image, compare_image)
print(results)
