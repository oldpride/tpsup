#!/usr/bin/env python

import os
import sys
import argparse
import textwrap
from pprint import pprint, pformat

import requests
import time
# from bs4 import BeautifulSoup
import re
from lxml import etree


def main():
    prog = os.path.basename(sys.argv[0])

    usage = textwrap.dedent("""
    generate fix tag definitions from local downloaded files. source: 
    https://www.onixs.biz/fix-dictionary/4.2/fields_by_tag.html 
    """)

    examples = textwrap.dedent(f"""
        examples:
        {prog} download_dir output.py
        {prog} ~/data/fix/4.4 fix_4_4.py
        """)

    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description=usage,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples)

    parser.add_argument(
        'dir', default=None, action='store',
        help='input dir')

    parser.add_argument(
        'output', default=None, action='store', help='fix protocol in python')

    parser.add_argument(
        '-v', '--verbose', default=0, action="count",
        help='verbose level: -v, -vv, -vvv')

    parser.add_argument(
        '-t', '--tags', dest="tags", default=None, action='store', type=str,
        help="only process these tags, eg, -t 54,38")

    args = vars(parser.parse_args())

    if args['verbose'] > 0:
        print(f'args =\n{pformat(args)}')

    sys.exit(parse_fix_download(**args))


def parse_fix_download(**opt):
    output = opt['output']
    _dir = opt['dir']

    verbose = 0
    if 'verbose' in opt and opt['verbose'] is not None:
        verbose = opt['verbose']

    if not os.path.exists(_dir):
        raise RuntimeError(f'cannot find {_dir}')

    field_by_tag = {}
    tag_by_field = {}
    file_by_tag = {}
    file_by_field = {}

    desc_by_tag_value = {}

    # Side <54>
    # b'<p>&#13;\n                  <a href="tagNum_54.html">Side &lt;54&gt;</a> of order&#13;\n
    # field_tag_pattern = r'^(\S+) <(.+?)>'
    field_tag_pattern = r'^FIX .+? : (\S+) <(.+?)>'
    compiled_field_tag_pattern = re.compile(field_tag_pattern)

    # 1 = Buy
    values_pattern = r'^(\S+) = (.*)'
    # values_pattern = r'^(\S+) = (.+)'
    # values_pattern = r'^(\S+) = ([^\(]+)'
    compiled_values_pattern = re.compile(values_pattern)

    valid_value_pattern = r'^Valid values:'
    compiled_valid_value_pattern = re.compile(valid_value_pattern, re.IGNORECASE)

    if 'tags' in opt and opt['tags']:
        tags = opt['tags'].split(',')
    else:
        tags = []

    class OutputFh:
        def __init__(self, filename: str, mode: str):
            self.filename = filename
            self.mode = mode
            self.need_close = False
            self.fh = None

        def __enter__(self):
            if self.filename == '-':
                self.fh = sys.stdout
            else:
                dirname = os.path.dirname(self.filename)
                if dirname:
                    os.makedirs(dirname, exist_ok=True)
                self.fh = open(self.filename, self.mode)
                self.need_close = True
            return self.fh

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.need_close:
                self.fh.close()
                self.fh = None

    with OutputFh(output, 'w') as ofh:
        for f in sorted(os.listdir(_dir)):
            if len(tags) > 0:
                skip = True

                for t in tags:
                    if f'_{t}.' in f:
                        skip = False
                        break
                if skip:
                    continue

            # f = 'tagNum_54.html'
            if f.startswith('tagNum_') and f.endswith('.html'):
                full_path = f'{_dir}/{f}'
                print('parsing ', full_path, file=sys.stderr)

                has_valid_values = False
                field_has_been_printed = False
                tag = None

                # open file in binary mode, otherwise, I get the following error
                # TypeError: reading file objects must return bytes objects
                with open(full_path, 'rb') as ifh:
                    # use event-driven lmxl parser for speed
                    # https://lxml.de/3.6/tutorial.html#the-parse-function
                    #
                    # file looks like
                    #                               <td>
                    #                                  <h2>FIX 4.4 : Side &lt;54&gt; field</h2>
                    #                               </td>
                    # ...
                    #                <p><a href="#UsedIn">Used In</a></p><a name="Description"></a>
                    #                   <h3>Description</h3>
                    #
                    #                <p>
                    #                   <a href="tagNum_54.html">Side &lt;54&gt;</a> of order
                    #                   this line is not reliable, for example, in 4.4/tagNum_38.html, this line
                    #                   points to tag 53.
                    #                </p>
                    #
                    #                <p>Valid values:</p>
                    #
                    #                <p>1 = Buy</p>
                    #
                    #                <p>2 = Sell</p>
                    for event, element in etree.iterparse(ifh, tag=('h2', 'p'), html=True):
                        # set html=True because etree.iterparse() by default parses xml only, but our file
                        # has <!doctype html>
                        if verbose > 0:
                            print('element.text = ', type(element.text), ':',  element.text)
                            print('etree.tostring(element) = ', etree.tostring(element))

                        if not element.text:
                            continue

                        if not field_has_been_printed:
                            if element.tag == 'h2':
                                h2 = element.text

                                m = compiled_field_tag_pattern.match(h2)
                                if m:
                                    if verbose > 0:
                                        print(field_tag_pattern, ' matched ', h2)

                                    field = m.group(1)
                                    tag = m.group(2)

                                    field_by_tag[tag] = field
                                    tag_by_field[field] = tag
                                    desc_by_tag_value[tag] = {}
                                    field_has_been_printed = True
                            continue

                        if element.tag != 'p':
                            continue

                        if not has_valid_values:
                            if compiled_valid_value_pattern.match(element.text):
                                has_valid_values = True
                            continue

                        m = compiled_values_pattern.match(element.text)
                        if m:
                            if verbose > 0:
                                print(values_pattern, ' matched ', element.text)
                            value = m.group(1)
                            desc = m.group(2)

                            if not desc:
                                # sometimes the description enclosed by <a>. for example in ~/data/fix/4.4 tag 35
                                #    <p>0 = <a href="msgType_0_0.html">Heartbeat &lt;0&gt;</a>
                                desc = element.findtext('a')

                            desc_by_tag_value[tag][value] = desc

                        element.clear(keep_tail=True)

        oldtag_by_newtag = {
            '54': '624',
            '77': '564',
        }

        for newtag, oldtag in oldtag_by_newtag.items():
            if newtag in desc_by_tag_value:
                desc_by_tag_value[oldtag] = desc_by_tag_value[newtag]

        print('field_by_tag = ', pformat(field_by_tag), file=ofh)
        print('tag_by_field = ', pformat(tag_by_field), file=ofh)
        print('desc_by_tag_value = ', pformat(desc_by_tag_value), file=ofh)


if __name__ == '__main__':
    main()
