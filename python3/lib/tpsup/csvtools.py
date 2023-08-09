import csv
import inspect
import io
import os
import pkgutil
import re
import sys
from pprint import pformat
from tpsup.tpfile import TpInput, TpOutput
from tpsup.tplog import log_FileFuncLine
from tpsup.util import convert_kvlist_to_dict, silence_BrokenPipeError
from tpsup.modtools import load_module, stringdict_to_funcdict, strings_to_compilable_func, \
    strings_to_compilable_patterns


def filter_dicts(dict_iter, columns, **opt):
    verbose = opt.get('verbose', 0)

    if verbose:
        log_FileFuncLine(f'opt =\n{pformat(opt)}\n', file=sys.stderr)

    if columns is not None:
        # make a copy to avoid changing original parameter
        out_fields = list(columns)
    else:
        out_fields = []

    ExportExps = opt.get('ExportExps', None)

    if ExportExps is not None:
        # ExportExps could be a dict or a list of key=value strings

        if isinstance(ExportExps, list):
            # format is kvlist: key=expression.
            # we need to convert it to dict
            ExportExps = convert_kvlist_to_dict(ExportExps)

        if isinstance(ExportExps, dict):
            out_fields.extend(ExportExps.keys())
        else:
            raise RuntimeError(
                f'ExportExps must be a dict or a list of key=value strings, actual type={type(ExportExps)}, value={pformat(ExportExps)}')

    # import pdb; pdb.set_trace();

    if verbose:
        print(f'__package__= {__package__}')
        print(f'__name__= {__name__}')

    source_list = []

    helper_file = 'csvtools_helper.py'

    if __package__ is not None:
        # this file is imported as module
        helper_data = pkgutil.get_data(__package__, helper_file)
        if helper_data is None:
            raise RuntimeError(
                f"missing {helper_file} or __init__.py in the same folder of csvtools.py")
        helper_source = helper_data.decode('utf-8')
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
        _list = opt.get(attr, [])
        source_list.append(strings_to_compilable_func(
            _list, attr, logic=logic, verbose=verbose))

    for attr in ['TempExps', 'ExportExps']:
        _dict = {}

        if opt.get(attr):
            if type(opt[attr]) == dict:
                # within python, it is easier to spec in dict
                _dict = opt[attr]
            elif type(opt[attr]) == list:
                # on command line, it is easier to spec in list of strings
                for pair in opt[attr]:
                    # split at the first occurrence
                    (key, value) = pair.split("=", 1)
                    _dict[key] = value

        source_list.append(stringdict_to_funcdict(
            _dict, attr, is_exp=1, verbose=verbose))

    source = '\n\n'.join(source_list)

    if verbose >= 2:
        log_FileFuncLine(f'source =\n{source}\n')

    if opt.get('SaveSource'):
        with open(opt['SaveSource'], 'wt') as f:
            f.write(source)
            f.write('\n')

    exp_module = load_module(source)

    match_exps = exp_module.MatchExps
    exclude_exps = exp_module.ExcludeExps
    temp_dict = exp_module.TempExps
    export_dict = exp_module.ExportExps

    for r in dict_iter:
        for name, func in temp_dict.items():
            r[name] = func(r)

        for name, func in export_dict.items():
            r[name] = func(r)

        if verbose > 1:
            sys.stderr.write(f'r = {pformat(r)}\n')

        if match_exps(r) and not exclude_exps(r):
            yield r


class QueryCsv:
    def __init__(self, filename, delimiter=',', **opt):
        self.verbose = opt.get('verbose', 0)
        self.reader = None
        self.tpi = None
        self.columns = None  # output columns
        self.filename = filename
        self.delimiter = delimiter
        self.opt = opt

    def __enter__(self):
        self.tpi = TpInput(filename=self.filename, need_header=1, **self.opt)
        self.reader = csv.DictReader(self.tpi.open())
        if self.opt.get('SelectFields'):
            self.columns = self.opt['SelectFields'].split(',')
        else:
            self.columns = self.reader.fieldnames
            # https://docs.python.org/3/library/csv.html#csv.DictWriter
            #     "this attribute is initialized upon first access or when the first record is read from the file."
            # This is likely by use the __get_attr__() trick when an attribute was missing from the object.
            # Therefore, when csv.DictWriter calls
            #     writer = csv.DictWriter(..., fieldnames=self.columns, ...)
            # reader.fieldnames will fetch the header line from the input file, and hence the header line will
            # be gone from the input afterwards. In this case, __iter__() will not yield the header row.
            # This part puzzled me quite a while because I couldn't figure out why the header line was gone4
            # and not yield by the __iter__()

            if self.columns is None:
                self.columns = []
                # this is to avoid this error when the input happened to be empty
                #   File "/usr/lib/python3.6/csv.py", line 143, in writeheader
                #     header = dict(zip(self.fieldnames, self.fieldnames))
                # TypeError: zip argument #1 must support iteration
        ExportExps = self.opt.get('ExportExps', None)
        if ExportExps is not None:
            # ExportExps could be a dict or a list of key=value strings

            if isinstance(ExportExps, list):
                # format is kvlist: key=expression.
                # we need to convert it to dict
                ExportExps = convert_kvlist_to_dict(ExportExps)

            if isinstance(ExportExps, dict):
                self.columns.extend(dict(ExportExps).keys())
            else:
                raise RuntimeError(
                    f'ExportExps must be a dict or a list of key=value strings. actual type={type(ExportExps)}, value={pformat(ExportExps)}')

        return self

    def __iter__(self):
        if not self.reader:
            # when without context manager:
            #     dictlist = list(QueryCsv(...))
            # or
            #     for dict in QueryCsv(...)
            with self:
                yield from self.iterator()
        else:
            # when called with context manager:
            # with QueryCsv(...) as qc:
            #      for row in qcL
            #          print(row)
            yield from self.iterator()

    def iterator(self):
        for row in filter_dicts(self.reader, self.reader.fieldnames, **self.opt):
            # print('__iter__', row)
            yield {key: value for key, value in row.items() if key in self.columns}

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __closed__(self) -> bool:
        return not self.tpi

    def close(self):
        if self.tpi:
            self.tpi.close()
            self.tpi = None

    def output(self, filename, **opt):
        # ofh = None
        #
        # # we have to declare ofh here, otherwise ofh is only defined in a function within a function, therefore
        # # is not in the closure. later, we also need announce 'nonlocal ofh'
        # # 'rows', on the other side, is defined in the function, not in a function of a function.
        #
        # def output_rows_to_ofh():
        #     odelim = opt.get('odelim', self.delimiter or ',')
        #     writer = csv.DictWriter(ofh, fieldnames=self.columns, delimiter=odelim)
        #     writer.writeheader()
        #     # rows is in this python's closure
        #     for row in rows:
        #         # print('debug2', row)
        #         writer.writerow(row)
        #
        # def output_rows():
        #     nonlocal ofh
        #     if isinstance(filename, io.StringIO):
        #         ofh = filename
        #         output_rows_to_ofh()
        #     else:
        #         with TpOutput(filename, **opt) as ofh:
        #             output_rows_to_ofh()

        if self.tpi:
            # if self.tpi is initiated, __enter__() must have been called, then we must be called by a context manager
            # eg
            #     with QueryCsv(...) as qc
            #         qc.output(...)
            #         columns = qc.columns
            # in this case, we don't need to use another context manager, just go ahead use self.tpi
            # print("output() called by a context manager")
            rows = self
            # output_rows()
            write_dictlist_to_csv(self, self.columns, filename, **opt)
        else:
            # print("output() not called by a context manager")
            # if self.tpi not initiated, __enter__() must not have been called, then we must not be called by a
            # context manager
            # eg
            #     qc = QueryCsv(...)
            #     qc.output(...)
            #     columns = qc.columns
            # or
            #     QueryCsv(...).output(...)
            with self as rows:
                # output_rows()
                write_dictlist_to_csv(self, self.columns, filename, **opt)


def write_dictlist_to_csv(dict_iter, columns, filename, **opt):
    ofh = None

    # we have to declare ofh here, otherwise ofh is only defined in a function within a function, therefore
    # is not in the closure. later, we also need announce 'nonlocal ofh'
    # 'rows', on the other side, is defined in the function, not in a function of a function.

    def output_rows_to_ofh():
        delimiter = opt.get('OutDelimiter', ',')
        if delimiter is None:
            delimiter = ','
        # print("type=", type(ofh)) print("tree=", inspect.getmro(type(ofh)))
        # tree = (<class 'gzip.GzipFile'>, < class '_compression.BaseStream' >, < class 'io.BufferedIOBase' >,
        # < class '_io._BufferedIOBase' >, < class 'io.IOBase' >, < class '_io._IOBase' >, < class 'object' > )
        #
        # >>> inspect.getmro(io.StringIO)
        # (<class '_io.StringIO'>, <class '_io._TextIOBase'>, <class '_io._IOBase'>, <class 'object'>)
        #
        # >>> isinstance(sys.stdin, io.TextIOBase)
        # True
        # >>> isinstance(sys.stderr, io.TextIOBase)
        # True
        # >>> isinstance(sys.stdout, io.TextIOBase)
        # True

        writer = csv.DictWriter(ofh, fieldnames=columns,
                                delimiter=delimiter, lineterminator=os.linesep)
        if ofh is sys.stdout:
            writer.writeheader = silence_BrokenPipeError(writer.writeheader)
            writer.writerow = silence_BrokenPipeError(writer.writerow)
        if not opt.get('PrintNoHeader'):
            writer.writeheader()
        # rows is in this python's closure
        for row in dict_iter:
            # print('debug2', row)
            new_row = {}
            for key in columns:
                if key in row:
                    new_row[key] = str(row[key])
                else:
                    new_row[key] = ""
            writer.writerow(new_row)

    if isinstance(filename, io.IOBase):
        if isinstance(filename, io.TextIOBase):
            ofh = filename
            output_rows_to_ofh()
        elif isinstance(filename, io.BufferedIOBase):
            # https://stackoverflow.com/questions/50120806/how-to-write-a-csv-file-in-binary-mode
            with io.TextIOWrapper(filename, encoding='utf-8', newline='') as ofh:
                output_rows_to_ofh()
        else:
            raise RuntimeError(
                f"io type = {type(filename)}\nclass tree = {inspect.getmro(type(filename))}")
    else:
        with TpOutput(filename, **opt) as unknown:
            if isinstance(unknown, io.TextIOBase):
                ofh = unknown
                output_rows_to_ofh()
            else:
                with io.TextIOWrapper(unknown, encoding='utf-8', newline='') as ofh:
                    output_rows_to_ofh()


def csv_to_dicts(filename: str, **opt):
    dicts = []
    for row in QueryCsv(filename=filename,  **opt):
        dicts.append(row)
    return dicts


def main():
    verbose = 0

    # if you run this script and pipe to 'head' command, you could get BrokenPipeError. disable the error with this line
    sys.stdout.write = silence_BrokenPipeError(sys.stdout.write)

    file = 'csvtools_test.csv'
    file_gz = 'csvtools_test.csv.gz'

    print(file)
    print(file_gz)
    print(f'\ntest1\n')

    with QueryCsv(filename=file, ExcludePatterns=['Smith'], verbose=verbose) as qc:
        for r in qc:
            print(r)

    print(f'\ntest2\n')
    with QueryCsv(filename=file, ExcludePatterns=['Smith'], verbose=verbose) as qc:
        writer = csv.writer(sys.stdout, delimiter=',')
        for r in qc:
            writer.writerow(r.values())

    print('\ntest3\n')
    qc = QueryCsv(filename=file, MatchPatterns=[
                  ',S'], ExcludePatterns=['Stephen'], verbose=verbose)
    qc.output(filename='-')
    qc.close()

    print('\ntest4\n')
    with QueryCsv(filename=file, MatchPatterns=[',S'], ExcludePatterns=['Stephen'], verbose=verbose) as qc:
        qc.output(filename='-')

    print('\ntest5\n')
    with QueryCsv(filename=file,
                  MatchExps=["r['name'].startswith('S')"],
                  ExcludeExps=["r['name'] == 'Stephen'"],
                  verbose=verbose) as qc:
        qc.output(filename='-')

    print('\ntest6\n')
    with QueryCsv(filename=file_gz,
                  MatchExps=["r['name'].startswith('S')"],
                  ExcludeExps=["r['name'] == 'Stephen'"],
                  verbose=verbose) as qc:
        qc.output(filename='-')

    print(f'\ntest7\n')
    for row in QueryCsv(filename=file, ExcludePatterns=['Smith'], verboske=verbose):
        print(row)

    print(f'\ntest8\n')
    output_file_gz = "/tmp/junk.gz"
    with QueryCsv(filename=file_gz,
                  MatchExps=["r['name'].startswith('S')"],
                  ExcludeExps=["r['name'] == 'Stephen'"],
                  verbose=verbose) as qc:
        write_dictlist_to_csv(qc, qc.columns, output_file_gz)
    os.system(f"gunzip -c {output_file_gz}")

    print(f'\ntest9\n')

    with QueryCsv(filename=file_gz, MatchExps=["r['name'].startswith('S')"], verbose=verbose) as qc,\
            TpOutput(output_file_gz) as ofh:
        write_dictlist_to_csv(qc, qc.columns, ofh)
    os.system(f"gunzip -c {output_file_gz}")


if __name__ == '__main__':
    main()
