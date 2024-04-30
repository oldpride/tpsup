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
    {prog} starting_url path1 path2 ... 

    web crawler to crawl a website and download files

    starting_url    the url to start the
    path1 path2 ... the xpath or css selector to match

    -h              print help

    -maxdepth int   max depth of the crawl, default 1

    -maxpage int    max number of pages to crawl, default 50

    -maxsize int    max size of the file to download, default 10 (MB).
    
    --download_dir dir
    -dd str         directory for downloading

    --processed_dir dir
    -pd str         directory for processing.
                    this is the folder that we run local web server.
    
    -v              verbose mode. -v -v for more verbose

    """)

examples = textwrap.dedent(f"""
examples:
    
    {prog} http://quotes.toscrape.com "xpath=//li[@class='next']/a" 

    <li class="next">
        <a href="/page/2/">
        Next
        <span aria-hidden="true">→</span>
        </a>
    </li>

    to get href
        "xpath=//li[@class='next']/a"
        "css=li.next > a"

    {prog} -dd dd -pd pd -maxdepth 1 sitebase/github/schoolproj/nyu_ds_java/course_slides.html "xpath=//ul/li/a" "xpath=//link[@rel='stylesheet']"

    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)

parser.add_argument(
    '-maxdepth', '--maxdepth', dest="maxdepth", action='store', type=int, default=1,
    help="depth of the crawl. default is 1")

parser.add_argument(
    '-maxpage', '--maxpage', dest="maxpage", action='store', type=int, default=50,
    help="max number of pages to crawl. default is 50")

parser.add_argument(
    '-maxsize', '--maxsize', dest="maxsize", action='store', type=int, default=10,
    help="max size of the file to download. default is 10 (MB)")

parser.add_argument(
    '-xpath', '--xpath', dest="xpath", action='store', type=str, default=None,
    help="xpath to match. default is None")

parser.add_argument(
    '-dd', '--download_dir', dest="download_dir", action='store', type=str, default=None,
    help="directory for downloading")

parser.add_argument(
    '-pd', '--processed_dir', dest="processed_dir", action='store', type=str, default=None,
    help="directory for processing")

parser.add_argument(
    '-v', '--verbose', dest="verbose", action='count', default=0,
    help="verbose mode. -v -v for more verbose")

parser.add_argument(
    'remainingArgs', default=None, nargs=argparse.REMAINDER,
    help='url and xpath')

args = vars(parser.parse_args())


if args['verbose']:
    sys.stderr.write(f"args =\n{pformat(args)}\n")

remainingArgs = args['remainingArgs']
if len(remainingArgs) < 2:
    sys.stderr.write("missing args\n")
    sys.stderr.write(usage)
    sys.stderr.write(examples)
    sys.exit(1)

start_url = remainingArgs[0]
paths = remainingArgs[1:]

maxpage = args['maxpage']
maxdepth = args['maxdepth']
maxsize = args['maxsize']
verbose = args['verbose']


crawler = tpsup.crawlertools.Crawler(
    start_url,
    paths,
    **args)
crawler.crawl()
