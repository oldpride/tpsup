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
from tpfile import TpInput, TpOutput


def main():
    verbose = 0

    file = 'csvwrapper_test.csv'
    print(f'\nfiltered\n')

    with QueryCsv(filename=file, MatchPatterns=[',S'], ExcludePatterns=['Smith'], verbose=verbose) as qc:
        for r in qc:
            print(r)

    QueryCsv(filename=file, MatchPatterns=[',S'], ExcludePatterns=['Smith'], verbose=verbose).output(output='-')


def filter_dict(dict_iter, columns, **opt):
    verbose = opt.get('verbose', 0)

    if verbose:
        sys.stderr.write(f'opt =\n{pformat(opt)}\n')

    out_fields = list(columns)  # make a copy to avoid changing original parameter

    if 'ExportExps' in opt:
        out_fields.extend(dict(opt['ExportExps']).keys())

    # import pdb; pdb.set_trace();

    if verbose:
        print(f'__package__= {__package__}')
        print(f'__name__= {__name__}')

    source_list = []

    helper_file = 'tpcsvtools_helper.py'

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
        _list = opt.get(attr, [])
        source_list.append(strings_to_compilable_func(_list, attr, logic=logic, verbose=verbose))

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

        source_list.append(stringdict_to_funcdict(_dict, attr, is_exp=1, verbose=verbose))

    source = '\n\n'.join(source_list)

    if verbose >= 2:
        print(f'source =\n{source}\n')

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
        self.tpi = TpInput(filename=self.filename, **self.opt)
        self.reader = csv.DictReader(self.tpi.open())
        return self.__iter__()

    def __iter__(self):
        if self.opt.get('SelectFields'):
            self.columns = self.opt['SelectFields'].split(',')
        else:
            self.columns = self.reader.fieldnames

        if self.opt.get('ExportExps'):
            self.columns.extend(dict(opt['ExportExps']).keys())

        for row in filter_dict(self.reader, self.reader.fieldnames, **self.opt):
            yield {key: value for key, value in row.items() if key in self.columns}

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __closed__(self) -> bool:
        return not self.tpi

    def close(self):
        if self.tpi:
            self.tpi.close()
            self.tpi = None

    def output(self, output, **_opt):
        with self as rows, TpOutput(output, **_opt) as tpo:
            odelim = _opt.get('odelim', self.delimiter or ',')
            writer = csv.writer(tpo, delimiter=odelim)
            for row in rows:
                writer.write_row(row)


if __name__ == '__main__':
    main()
