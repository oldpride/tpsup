import sys
import re
from pprint import pprint, pformat
from tpsup.util import strings_to_compiled_list, load_module
import csv
import io


# learned from the Cookbook (8.3)
class CsvEntry(io.BytesIO):
    def __init__(self, filename, **opt):
        super().__init__()
        self.filename = filename
        self.opt = opt
        self.columns = None
        self.delimiter = None
        self.fh = None

    def readline(self, size=-1):
        source_list = ['import re']

        opt = self.opt

        verbose = 0

        if 'verbose' in opt and opt['verbose'] != 0:
            verbose = 1

        for attr in ['MatchPattern', 'ExcludePattern']:
            if attr in opt and opt[attr] is not None:
                # need to convert pattern string into bytes-like object as we read the csv as binary data
                strings = opt[attr]
            else:
                strings = []

            source_list.append(strings_to_compiled_list(strings, attr))

        source = '\n\n'.join(source_list)

        if verbose:
            sys.stderr.write(f'source code = \n{source}\n')

        pattern_filter = load_module(source)

        match_patterns = pattern_filter.MatchPattern
        exclude_patterns = pattern_filter.ExcludePattern

        # this 'with' is a context-manager
        with self.fh as fh:
            while 1:
                # line = fh.readline()
                line = next(fh)
                if not line:
                    break

                line = line.rstrip()

                # https://docs.python.org/2/howto/regex.html
                # match() Determine if the RE matches at the beginning of the string.
                # search() Scan through a string, looking for any location where this RE matches.
                # findall() Find all substrings where the RE matches, and returns them as a list.
                # finditer() Find all substrings where the RE matches, and returns
                # them as an iterator.

                matched = 1

                for compiled in match_patterns:
                    # if not compiled.match(line):
                    if not compiled.search(line):
                        matched = 0
                        break

                if not matched:
                    continue

                excluded = 0

                for compiled in exclude_patterns:
                    if compiled.search(line):
                        excluded = 1
                        break
                if excluded:
                    continue

                yield line

    def closed(self) -> bool:
        if self.fh is None:
            return True
        else:
            return False

    def __enter__(self):
        opt = self.opt
        filename = self.filename

        if 'skip' in opt and opt['skip']:
            skip = opt['skip']
        else:
            skip = 0

        if 'delimiter' in opt and opt['delimiter']:
            delimiter = opt['delimiter']
        else:
            delimiter = ','

        # https://stackoverflow.com/questions/1984104/how-to-avoid-explicit-self-in-python
        # python requires prefix self
        fh = None
        if filename == '-':
            fh = sys.stdin
        else:
            # the unicode-sandwich design pattern
            if filename.endswith('.gz'):
                fh = gzip.open(filename, 'r', encoding='utf-8')
            else:
                fh = open(filename, 'r', encoding='utf-8')

        # skip lines if needed
        for count in range(0, skip):
            line = fh.readline()

            if not line:
                raise RuntimeError(f'{filename} has only {count} lines; but need to skip {skip}')

        header_line = fh.readline()

        if not header_line:
            raise RuntimeError(f'{filename} missing header. {skip} lines skipped')

        header_line = header_line.rstrip()

        self.columns = header_line.split(delimiter)
        self.delimiter = delimiter
        self.fh = fh

        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.fh.close()
        self.fh = None

    def __iter__(self):
        return self.readline()

    def __next__(self):
        return self.readline()


def csv_to_dict_stream(filename, **opt):
    with CsvEntry(filename, **opt) as csv_entry:
        columns = csv_entry.columns

        # https://stackoverflow.com/questions/51152023/how-to-use-python-csv-dictreader-with-a-binary-file-for-a-babel-custom-extract
        dict_reader = csv.DictReader(csv_entry, fieldnames=columns)
        for row in dict_reader:
            yield row


def main():
    file = 'csv_test.csv'

    sys.stdout.flush()

    print(f'filtered')

    with CsvEntry(file, MatchPattern=[',S'], ExcludePattern=['Smith'], verbose=1) as csv_entry:
        for row in csv_entry.readline():
            print(row)

    sys.stdout.flush()

    print(f'\nuse csv module')

    dict_stream = csv_to_dict_stream(file, MatchPattern=[',S'], verbose=1)
    for row in dict_stream:
        print(row)

    print(f'\nopen gz file')

    dict_stream = csv_to_dict_stream(file, MatchPattern=[',H'], verbose=1)
    for row in dict_stream:
        print(row)


if __name__ == '__main__':
    main()



# def query_csv(**opt):
#     if 'verbose' in opt and opt['verbose']:
#         sys.stderr.write(f'opt =\n{pformat(opt)}\n')
#
#     if 'input' not in opt or opt['input'] is None:
#         raise RuntimeError('missing "input"" setting')
#
#     # import pdb; pdb.set_trace();
#
#     if 'input_type' not in opt:
#         return None
#
#     if opt['input_type'] == 'file':
#         CsvEntry(opt['input'], **opt)
#     elif opt['input_type'] == 'struct':
#         csv_struct = opt['input']
#
#         for attr in ['array', 'columns', 'delimiter']:
#             if not attr in csv_struct:
#                 print >> sys.stderr, "opt['struct'] missing key=" + attr
#                 sys.exit(1)
#     else:
#         print >> sys.stderr, "unknow input_type=", opt['input_type']
#
#     if 'error' in csv_struct:
#         return csv_struct
#
#     if 'verbose' in opt and opt['verbose']:
#         print >> sys.stderr, 'csv_struct = ', pformat(csv_struct)
#
#     rows = csv_struct['array']
#     columns = csv_struct['columns']
#     delimiter = csv_struct['delimiter']

#     # exec("def test_exp(): return r['alpha'] is 'c'")
#     MatchExp = None
#     ExcludeExp = None
#
#     for Exp in ['MatchExp', 'ExcludeExp']:
#         if (Exp in opt and opt[Exp] != None):
#             uncompiled = "def " + Exp + "(r):\n"
#             if (Exp == 'MatchExp'):
#                 for e in opt[Exp]:
#                     uncompiled += "    if not " + e + ":\n"
#                     uncompiled += "        return False\n"
#
#                 uncompiled += "    return True\n"
#             else:
#                 # Exp == 'ExcludeExp'
#                 for e in opt[Exp]:
#                     uncompiled += "    if " + e + ":\n"
#                     uncompiled += "        return True\n"
#
#                 uncompiled += "    return False\n"
#             if 'verbose' in opt and opt['verbose']:
#                 print >> sys.stderr, Exp, "uncompiled = ", uncompiled
#
#             # exec("def test_exp(r): return "    + opt['MatchExp'])
#             exec(uncompiled)
#         else:
#             if (Exp == 'MatchExp'):
#                 exec("def " + Exp + "(r): return True")
#             elif (Exp == 'ExcludeExp'):
#                 exec("def " + Exp + "(r): return False")
#
#     temp_fields = []
#     func_by_field = {}
#
#     if 'TempExp' in opt and opt['TempExp'] != None:
#         i = 0
#         for string in opt['TempExp']:
#             m = re.match('^([^=]+)=(.+)', string)
#             col = m.group(1)
#             exp = m.group(2)
#
#             func_name = "ef_" + str(i)
#
#             uncompiled = "def " + func_name + "(r): return " + exp
#             if 'verbose' in opt and opt['verbose']:
#                 print >> sys.stderr, "temp col = " + col + " uncompiled = ", uncompiled
#
#             exec(uncompiled)
#
#             temp_fields.append(col)
#
#             exec("func_by_field['" + col + "'] = " + func_name)
#
#             i += 1
#
#         if 'verbose' in opt and opt['verbose']:
#             print >> sys.stderr, "func_by_field = ", pformat(func_by_field)
#             print >> sys.stderr, "temp_fields = ", pformat(temp_fields)
#
#     if 'fields' in opt and opt['fields']:
#         fields = opt['fields'].split(",")
#     else:
#         fields = columns + temp_fields
#
#     csv_struct2 = {}
#
#     rows2 = []
#
#     for row in rows:
#         for f in temp_fields:
#             func = func_by_field[f]
#             row[f] = func(row)
#
#         if 'verbose' in opt and opt['verbose']:
#             print >> sys.stderr, "row = ", pformat(row);
#
#         # MatchExp() and ExcludeExp() were inserted using exec. TODO: delete this confusion
#         if MatchExp(row) and not ExcludeExp(row):
#             rows2.append(row)
#
#     csv_struct2['array'] = rows2
#     csv_struct2['delimiter'] = delimiter
#     csv_struct2['columns'] = fields
#
#     if 'output' in opt:
#         print_csv_dict(csv_struct2['array'], csv_struct2['columns'], opt['output'], **opt)
#
#     return csv_struct2
#
#
# def print_csv_dict(_dict_rows, _fields, _output, **opt):
#     if 'verbose' in opt and opt['verbose']:
#         print >> sys.stderr, "print_csv_dict opt = ", pformat(opt);
#
#     ofo = None
#
#     if _output == '-':
#         ofo = sys.stdout
#     else:
#         ofo = open(_output, 'w')
#
#     odelimiter = None
#
#     if 'odelimiter' in opt and opt['odelimiter'] != None:
#         odelimiter = opt['odelimiter']
#     elif 'delimiter' in opt and opt['delimiter'] != None:
#         odelimiter = opt['delimiter']
#     else:
#         odelimiter = ','
#
#     if 'verbose' in opt and opt['verbose']:
#         print >> sys.stderr, "ofo = ", pformat(ofo);
#         print >> sys.stderr, "odelimiter = ", odelimiter;
#
#     ofo.write(odelimiter.join(_fields) + "\n")
#
#     for row in _dict_rows:
#         list = []
#
#         for f in _fields:
#             if not f in row:
#                 value = ''
#             else:
#                 value = row[f]
#
#             list.append(value)  # this does    append '' to the list
#             # list += value     #this doesn't append '' to the list
#
#         if 'verbose' in opt and opt['verbose']:
#             print >> sys.stderr, "print_csv_dict row = ", pformat(row);
#             print >> sys.stderr, "print_csv_dict list = ", pformat(list);
#
#         # map(function, iterable) applies a function to every item of the iterable and return a list.
#         ofo.write(odelimiter.join(map(str, list)) + "\n")
