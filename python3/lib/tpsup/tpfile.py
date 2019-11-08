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


class TpInput:
    def __init__(self, filename, **opt):
        self.verbose = opt.get('verbose', 0)
        self.filename = filename
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

    def open(self):
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

    def close(self):
        if self.need_close_fh:
            self.fh.close()
        self.fh = None
        self.need_close_fh = False

    def closed(self) -> bool:
        return not self.fh

    def __iter__(self):
        return self.readline()

    def __enter__(self):
        return self.__open__()

    def __exit__(self, exec_type, exc_value, traceback):
        self.close()


class TpOutput:
    def __init__(self, filename, **opt):
        self.verbose = opt.get('verbose', 0)
        self.filename = filename
        self.need_close_fh = False
        self.fh = None

    def __enter__(self):
        if self.filename == '-':
            self.fh = sys.stdout
        else:
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)
            self.fh = open(self.filename, 'w', encoding='utf-8')
            self.need_close_fh = True
        return self.fh

    def close(self):
        if self.need_close_fh:
            self.fh.close()
        self.fh = None
        self.need_close_fh = False

    def closed(self) -> bool:
        return not self.fh

    def __exit__(self, exec_type, exc_value, traceback):
        self.close()


def main():
    verbose = 0

    file = 'csvwrapper_test.csv'
    print(f'\nfiltered\n')

    with TpInput(filename=file, MatchPatterns=[',S'], ExcludePatterns=['Smith'], verbose=verbose) as tf:
        for line in tf:
            print(line)

    import csv
    with TpInput(filename=file, ExcludePatterns=['Smith'], verbose=verbose) as tf:
        reader = csv.DictReader(tf)
        headers = reader.fieldnames
        print(headers)
        for row in reader:
            pprint(row)


if __name__ == '__main__':
    main()
