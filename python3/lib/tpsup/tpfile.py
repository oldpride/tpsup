from glob import glob
import gzip
import os
import re
import sys
from pprint import pformat, pprint
from typing import Union
from tpsup.modtools import strings_to_compilable_patterns, load_module
from tpsup.tplog import log_FileFuncLine
from tpsup.util import silence_BrokenPipeError


class TpInput:
    def __init__(self, filename, **opt):
        self.verbose = opt.get('verbose', 0)
        self.need_header = opt.get('need_header', False)
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

                self.fh = gzip.open(self.filename, 'rt',
                                    encoding='utf-8', newline='')
            else:
                self.fh = open(self.filename, 'r',
                               encoding='utf-8', newline='')

        for count in range(0, self.skip):
            try:
                next(self.fh)
            except StopIteration:
                break
        return self

    def readline(self):
        line_number = 0

        for line in self.fh:
            line_number += 1

            if line_number == 1 and self.need_header:
                # csv module needs the header line
                yield line
                continue

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

            # print(f'iamhere {line}')
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
        return self.open()

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
            # overwrite a standard function
            self.fh.write = silence_BrokenPipeError(self.fh.write)
        else:
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)
            self.need_close_fh = True
            if self.filename.endswith('.gz'):
                self.fh = gzip.open(self.filename, 'wb')
            else:
                self.fh = open(self.filename, 'w', encoding='utf-8')
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


def tpglob(file: Union[list, str],  **opt):
    if isinstance(file, str):
        files = file.split()
    elif isinstance(file, list):
        files = file
    else:
        raise RuntimeError(
            f'unsupported type of file={pformat(file)}\nIt must be a list or a string')

    files2 = []
    for f in files:
        if f == '-':
            # this is stdin
            files2.append(f)
        else:
            globbed = glob(f)
            if not globbed:
                log_FileFuncLine(f'{f} not found', file=sys.stderr)
                continue
            files2.extend(globbed)

    return files2


def sorted_files(files: Union[list, str], sort_func, globbed: bool = False, **opt):
    if not globbed:
        files2 = tpglob(files, **opt)
    else:
        files2 = files

    return list(sorted(files2, key=sort_func))


def sorted_files_by_mtime(files: list, **opt):
    return sorted_files(files, os.path.getmtime, **opt)


def main():
    verbose = 1

    file = 'csvtools_test.csv'
    testdir = '/tmp/junkdir'
    file_gz = f'{testdir}/junk.csv.gz'
    print('test1')

    with TpInput(filename=file, ExcludePatterns=['Smith'], verbose=verbose) as tf:
        for line in tf:
            print(line, end='')

    print('test2')
    import csv
    with TpInput(filename=file, MatchPatterns=[',S'], ExcludePatterns=['Stephen'], verbose=verbose) as tf:
        reader = csv.DictReader(tf)
        headers = reader.fieldnames
        print(headers)
        for row in reader:
            pprint(row)

    print('test3')
    os.system(f'/bin/rm -fr {testdir}')
    with TpInput(filename=file, MatchPatterns=[',S'], ExcludePatterns=['Stephen'], verbose=verbose) as ti, \
            TpOutput(filename=file_gz) as to:
        for line in ti:
            to.write(line.encode('utf-8'))

    os.system(f'ls -l {file_gz}; zcat {file_gz}; /bin/rm -fr {testdir}')

    from tpsup.exectools import test_lines
    TPSUP = os.environ.get('TPSUP')
    libfiles = f'{TPSUP}/python3/lib/tpsup/*.py'

    def test_codes():
        sorted_files_by_mtime([libfiles], verbose=verbose)

    test_lines(test_codes, source_globals=globals(), source_locals=locals())


if __name__ == '__main__':
    main()
