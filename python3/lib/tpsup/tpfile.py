import sys
import re
from pprint import pprint, pformat
from tpsup.util import strings_to_compilable_patterns, load_module, stringdict_to_funcdict, strings_to_compilable_func
import io
import gzip
import pkgutil
import inspect
import os
from typing import Dict, List


class TpFile:
    def __init__(self, **opt):
        self.verbose = opt.get('verbose', 0)
        self.filename = opt.get('filename', None)
        self.need_close_fh = False
        self.fh = None

        source_list = ['import re']

        for attr in ['MatchPatterns', 'ExcludePatterns']:
            # need to convert pattern string into bytes-like object as we read the csv as binary data
            strings = opt.get(attr, [])
            source_list.append(strings_to_compilable_patterns(strings, attr))

        source = '\n\n'.join(source_list)

        if self.verbose >= 2:
            sys.stderr.write(f'source code = \n{source}\n')

        pattern_filter = load_module(source)

        self.match_patterns = pattern_filter.MatchPatterns
        self.exclude_patterns = pattern_filter.ExcludePatterns

        self.skip = opt.get('skip', 0)

    def __enter__(self):
        if self.filename == '-':
            self.fh = sys.stdin
        else:
            self.need_close_fh = True
            # the unicode-sandwich design pattern
            if self.filename.endswith('.gz'):
                # in /usr/lib/python/3.6/gzip.py, open()
                # if "t" in mode:
                #     if "b" in mode:
                #         raise ValueError("Invalid mode: %r" % (mode,))
                # else:
                #     if encoding is not None:
                #         raise ValueError("Argument 'encoding' not supported in binary mode")
                #     if errors is not None:
                #         raise ValueError("Argument 'errors' not supported in binary mode")
                #     if newline is not None:
                #         raise ValueError("Argument 'newline' not supported in binary mode")

                self.fh = gzip.open(self.filename, 'rt', encoding='utf-8', newline='')
            else:
                self.fh = open(self.filename, 'r', encoding='utf-8', newline='')

        for count in range(0, self.skip):
            try:
                next(self.fh)
            except StopIteration:
                break
        return self

    def readline(self):
        for line in self.fh:
            matched = 1

            for compiled in self.match_patterns:
                # if not compiled.match(line):
                if not compiled.search(line):
                    matched = 0
                    break

            if not matched:
                continue

            excluded = 0

            for compiled in self.exclude_patterns:
                if compiled.search(line):
                    excluded = 1
                    break
            if excluded:
                continue

            yield line
        return

    def closed(self) -> bool:
        if self.fh is None:
            return True
        else:
            return False

    def __iter__(self):
        return self.readline()

    def __exit__(self, exec_type, exc_value, traceback):
        if self.need_close_fh:
            print('closing')
            self.fh.close()
            self.fh = None


def main():
    verbose = 0

    file = 'csvwrapper_test.csv'
    print(f'\nfiltered\n')

    with TpFile(filename=file, MatchPatterns=[',S'], ExcludePatterns=['Smith'], verbose=verbose) as tf:
        for line in tf:
            print(line)

    import csv
    with TpFile(filename=file, ExcludePatterns=['Smith'], verbose=verbose) as tf:
        reader = csv.DictReader(tf)
        headers = reader.fieldnames
        print(headers)
        for row in reader:
            pprint(row)

if __name__ == '__main__':
    main()
