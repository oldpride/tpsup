import sys
import re
from pprint import pprint, pformat
from tpsup.util import strings_to_compilable_patterns, load_module, stringdict_to_funcdict, strings_to_compilable_func
import csv
import io
import gzip
import pkgutil
import inspect
import os
from typing import Dict, List

"""
why do we need this ?
    standard csv cannot filter input file by line-based pattern, eg, cannot do 'grep 'col1,col2'.
why do will still use standard csv module?
    standard csv has sophisticated parser to parse quoted columns. and we don't want to reinvent the wheels.

steps:
- open file.
- filter input, line-based.
- pass csv.dictReader a fileObj.
- standard csv module generates dict list.
- filter dict list, column-based.

"""


# learned from the Cookbook (8.3)
# I cannot add context manager into CsvEntry because in order to get columns I have to open and parse the file.
# If use context manager, opening the file should be part of __enter__(). but often time, calling function wanted
# to get columns information before iteration, ie, before the context management. Therefore, opening and parsing the
# file (at least till the header line) should be part of __init__().
class CsvEntry(io.BytesIO):
    def __init__(self, filename, **opt):
        super().__init__()
        self.filename = filename
        self.opt = opt
        self.verbose = 0
        self.fh = None
        self.columns = None

        if 'verbose' in opt and opt['verbose'] != 0:
            self.verbose = opt['verbose']
        else:
            self.verbose = 0

        source_list = ['import re']

        for attr in ['MatchPatterns', 'ExcludePatterns']:
            if attr in opt and opt[attr] is not None:
                # need to convert pattern string into bytes-like object as we read the csv as binary data
                strings = opt[attr]
            else:
                strings = []

            source_list.append(strings_to_compilable_patterns(strings, attr))

        source = '\n\n'.join(source_list)

        if self.verbose >= 2:
            sys.stderr.write(f'source code = \n{source}\n')

        pattern_filter = load_module(source)

        self.match_patterns = pattern_filter.MatchPatterns
        self.exclude_patterns = pattern_filter.ExcludePatterns

        if 'skip' in opt and opt['skip']:
            self.skip = opt['skip']
        else:
            self.skip = 0

        if 'delimiter' in opt and opt['delimiter']:
            self.delimiter = opt['delimiter']
        else:
            self.delimiter = ','

        if self.filename == '-':
            fh = sys.stdin
        else:
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

                fh = gzip.open(self.filename, 'rt', encoding='utf-8', newline='')
                self.need_close_fh = 1
            else:
                fh = open(self.filename, 'r', encoding='utf-8', newline='')

            # If newline='' is not specified, newlines embedded inside quoted fields will not be interpreted
            # correctly, and on platforms that use \r\n linendings on write an extra \r will be added. It should
            # always be safe to specify newline='', since the csv module does its own (universal) newline handling.
            # https://docs.python.org/3/library/csv.html

        # skip lines if needed
        for count in range(0, self.skip):
            line = fh.readline()

            if not line:
                raise RuntimeError(f'{filename} has only {count} lines; but need to skip {skip}')

        header_line = fh.readline()

        if not header_line:
            raise RuntimeError(f'{filename} missing header after {skip} lines skipped')

        header_line = header_line.rstrip()

        self.columns = header_line.split(self.delimiter)
        if self.verbose > 0:
            print(f'columns = {self.columns}', file=sys.stderr)
        self.fh = fh

    def readline(self, size=-1):
        # # this 'with' is a context-manager
        # with self.fh as fh:
        while 1:
            try:
                # line = fh.readline()
                line = next(self.fh)
                if not line:
                    break

                # https://docs.python.org/2/howto/regex.html
                # match() Determine if the RE matches at the beginning of the string.
                # search() Scan through a string, looking for any location where this RE matches.
                # findall() Find all substrings where the RE matches, and returns them as a list.
                # finditer() Find all substrings where the RE matches, and returns
                # them as an iterator.

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
            except StopIteration:
                # self.__exit__()
                return
                # https://stackoverflow.com/questions/43617399/how-to-get-rid-of-warning-deprecationwarning-generator-ngrams-raised-stopiter
                # https://www.python.org/dev/peps/pep-0479/

    def closed(self) -> bool:
        if self.fh is None:
            return True
        else:
            return False

    # def __enter__(self):
    #     if self.verbose > 0:
    #         print(f'__enter__() CsvEntry', file=sys.stderr)
    #     # https://stackoverflow.com/questions/1984104/how-to-avoid-explicit-self-in-python
    #     # python requires prefix self

    # def __exit__(self, exc_type, exc_value, tb):
    # base class's __exit__() is build-in function. I cannot figure out its signature.
    # def __exit__(self, *args, **kwargs):
    #     if self.verbose > 0:
    #         print(f'__exit__() CsvEntry', file=sys.stderr)
    #     if self.need_close_fh == 1:
    #         if self.verbose > 0:
    #             print(f'actually closing fh', file=sys.stderr)
    #         self.fh.close()
    #     self.fh = None

    def __iter__(self):
        return self.readline()

    def __next__(self):
        return self.readline()

    def close(self) -> None:
        if self.fh != sys.stdin:
            self.fh.close()


# list vs array
# https://stackoverflow.com/questions/176011/python-list-vs-array-when-to-use
# Basically, Python lists are very flexible and can hold completely heterogeneous,
# arbitrary data, and they can be appended to very efficiently, in amortized constant
# time. If you need to shrink and grow your list time-efficiently and without hassle,
# they are the way to go. But they use a lot more space than C arrays.
#
# The array.array type, on the other hand, is just a thin wrapper on C arrays. It can
# hold only homogeneous data, all of the same type, and so it uses only
# sizeof(one object) * length bytes of memory. Mostly, you should use it when you need
# to expose a C array to an extension or a system call (for example, ioctl or fctnl).
#
# array.array is also a reasonable way to represent a mutable string in Python 2.x
# (array('B', bytes)). However, Python 2.6+ and 3.x offers a mutable byte string as
# bytearray.
#
# However, if you want to do math on a homogeneous array of numeric data, then you're
# much better off using NumPy, which can automatically vectorize operations on complex
# multi-dimensional arrays.

class CsvDictList:
    # the following doesn't make much sense as __iter__ and __next are the same, but it works
    def __init__(self, filename: str, **opt):
        self.csv_entry = CsvEntry(filename, **opt)
        self.filename = filename
        self.opt = opt

        columns = self.csv_entry.columns
        opt = self.opt

        out_fields = []

        if 'SelectFields' in opt and opt['SelectFields'] is not None:
            out_fields.extend(str(opt['SelectFields']).split(','))
        else:
            out_fields.extend(columns)

        if 'ExportExps' in opt and opt['ExportExps'] is not None:
            out_fields.extend(dict(opt['ExportExps']).keys())

        self.columns = out_fields

    def iterator(self):
        opt = self.opt
        out_columns = self.columns

        # https://stackoverflow.com/questions/51152023/how-to-use-python-csv-dictreader-with-a-binary-file-for-a-babel-custom-extract
        dict_reader = csv.DictReader(self.csv_entry, fieldnames=self.csv_entry.columns)

        for row in filter_dictlist(dict_reader, **opt):
            new_row = {key: value for key, value in row.items() if key in out_columns}
            yield new_row
        self.csv_entry.close()
        return

    def __iter__(self):
        return self.iterator()

    def __next__(self):
        return self.iterator()


def main():
    verbose = 0

    file = 'csvwrapper_test.csv'
    print(f'\nfiltered\n')

    csv_entry = CsvEntry(file, MatchPatterns=[',S'], ExcludePatterns=['Smith'], verbose=verbose)
    for row in csv_entry:
        print(row)
    csv_entry.close()

    # sys.stdout.flush()

    print(f'\nuse csv module\n')

    dictlist = CsvDictList(file, MatchPatterns=[',S'], verbose=verbose)
    for row in dictlist:
        print(row)

    gz_file = 'csvwrapper_test.csv.gz'
    print(f'\nopen gz file {gz_file}\n')

    dictlist = CsvDictList(gz_file, MatchPatterns=[',H'], verbose=verbose)

    for row in dictlist:
        print(row)

    print(f'\nquery csv\n')
    dictlist = CsvDictList(filename=file,
                           MatchExps=['str(r["name"]).startswith("J")'],
                           TempExps={'tempcol1': 'r["name"]+"-"+r["number"]'},
                           ExportExps={'exportcol1': 'r["tempcol1"] + "-confirmed"'},
                           verbose=verbose)

    for row in dictlist:
        print(row)

    print(f'\nprint to stdout\n')

    query_csv(filename=file,
              MatchExps=['str(r["name"]).startswith("J")'],
              ExcludeExps=['int(r["number"])>2'],
              TempExps={'tempcol1': 'r["name"]+"-"+r["number"]'},
              ExportExps={'exportcol1': 'r["tempcol1"] + "-confirmed"'},
              Output='-',
              verbose=verbose)

    print(f'\ndone\n')


def filter_dictlist(dictlist: List[Dict[str, str]], **opt) -> List[Dict[str, str]]:
    if 'verbose' in opt and opt['verbose'] != 0:
        verbose = opt['verbose']
        sys.stderr.write(f'opt =\n{pformat(opt)}\n')
    else:
        verbose = 0

    # import pdb; pdb.set_trace();

    if verbose > 0:
        print(f'__package__= {__package__}')
        print(f'__name__= {__name__}')

    source_list = []

    helper_file = 'csvwrapper_helper.py'

    if __package__ is not None:
        # this file is imported as module
        helper_source = pkgutil.get_data(__package__, helper_file).decode('utf-8')
        source_list.append(helper_source)
    else:
        # this file is run as a script
        filename = inspect.getframeinfo(inspect.currentframe()).filename
        path = os.path.dirname(os.path.abspath(filename))

        helper_file = f'{path}/{helper_file}'

        # read the entire file
        with open(helper_file, 'r') as f:
            source_list.append(f.read())

    for attr, logic in [('MatchExps', 'and'), ('ExcludeExps', 'or')]:
        if attr in opt and opt[attr] is not None:
            _list = opt[attr]
        else:
            _list = []
        source_list.append(strings_to_compilable_func(_list, attr, logic=logic, verbose=verbose))

    for attr in ['TempExps', 'ExportExps']:
        _dict = {}

        if attr in opt and opt[attr] is not None:
            if type(opt[attr]) == dict:
                # within python, it is easier to spec in dict
                _dict = opt[attr]
            elif type(opt[attr]) == list:
                # on command line, it is easier to spec in list of strings
                for pair in opt[attr]:
                    # split at the first occurrence
                    (key, value) = pair.split("=", 1)
                    _dict[key] = value

        source_list.append(stringdict_to_funcdict(_dict, attr, is_exp=1, verbose=verbose))

    source = '\n\n'.join(source_list)

    if verbose >= 2:
        print(f'source =\n{source}\n')

    if 'SaveSource' in opt and opt['SaveSource'] is not None:
        with open(opt['SaveSource'], 'wt') as f:
            f.write(source)
            f.write('\n')

    exp_module = load_module(source)

    match_exps = exp_module.MatchExps
    exclude_exps = exp_module.ExcludeExps
    temp_dict = exp_module.TempExps
    export_dict = exp_module.ExportExps

    for r in dictlist:
        for name, func in temp_dict.items():
            r[name] = func(r)

        for name, func in export_dict.items():
            r[name] = func(r)

        if verbose >= 1:
            sys.stderr.write(f'r = {pformat(r)}\n')

        if match_exps(r) and not exclude_exps(r):
            yield r


def write_csv(csv_writer, dictlist: List[Dict[str, str]], _fields: List[str], **opt):
    csv_writer.writeheader()

    for row in dictlist:
        # cookbook 1.17
        new_row = {key: value for key, value in row.items() if key in _fields}
        csv_writer.writerow(new_row)


def query_csv(**opt):
    if 'filename' not in opt or opt['filename'] is None:
        raise RuntimeError('missing "filename"" setting')
    else:
        filename = opt['filename']

    if 'Output' not in opt or opt['Output'] is None:
        raise RuntimeError(f"opt['Output'] is not defined")

    del opt['filename']
    dictlist = CsvDictList(filename, **opt)
    columns = dictlist.columns
    delimiter = dictlist.csv_entry.delimiter

    if 'OutDelimiter' in opt and opt['OutDelimiter'] is not None:
        out_delimiter = opt['OutDelimiter']
    else:
        out_delimiter = delimiter

    if opt['Output'] == '-':
        csv_writer = csv.DictWriter(sys.stdout, fieldnames=columns, delimiter=out_delimiter)
        write_csv(csv_writer, dictlist, columns, **opt)
    elif isinstance(opt['Output'], io.IOBase):
        # https://stackoverflow.com/questions/1549801/what-are-the-differences-between-type-and-isinstance
        #
        # isinstance caters for inheritance (an instance of a derived class is an instance of a base class, too),
        # while checking for equality of type does not (it demands identity of types and rejects instances of
        # subtypes, AKA subclasses).
        csv_writer = csv.DictWriter(opt['Output'], fieldnames=columns, delimiter=out_delimiter)
        write_csv(csv_writer, dictlist, columns, **opt)
    else:
        with open(opt['Output'], 'w') as out_fh:
            csv_writer = csv.DictWriter(out_fh, fieldnames=columns, delimiter=out_delimiter)
            write_csv(csv_writer, dictlist, columns, **opt)


if __name__ == '__main__':
    main()
