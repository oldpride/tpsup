import sys
import re
from pprint import pprint, pformat
from tpsup.util import strings_to_compiled_list, load_module


# learned from the Cookbook (8.3)
class TpCsv:
    def __init__(self, filename, **opt):
        self.filename = filename
        self.opt = opt

    def __enter__(self):
        tpcsv = {}
        opt = self.opt
        filename = self.filename

        if 'skip' in opt and opt['skip']:
            skip = opt['skip']
        else:
            skip = 0

        if 'delimiter' in opt and opt['delimiter']:
            delimiter = opt['delimiter'].encode('utf-8')
        else:
            delimiter = ','.encode('utf-8')

        # https://stackoverflow.com/questions/1984104/how-to-avoid-explicit-self-in-python
        # python requires prefix self
        fh = None
        if filename == '-':
            fh = sys.stdin
        else:
            if filename.endswith('.gz'):
                fh = gzip.open(filename, 'rb')
            else:
                fh = open(filename, 'rb')

        # skip lines if needed
        for count in range(0, skip):
            line = fh.readline()

            if not line:
                raise RuntimeError(f'{filename} has only {count} lines; but need to skip {skip}')

        header_line = fh.readline()

        if not header_line:
            raise RuntimeError(f'{filename} missing header. {skip} lines skipped')

        header_line = header_line.rstrip()

        tpcsv['columns'] = header_line.split(delimiter)
        tpcsv['delimiter'] = delimiter
        tpcsv['filename'] = filename
        tpcsv['fh'] = fh

        self.tpcsv = tpcsv

        return tpcsv

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tpcsv['fh'].close()


def csv_to_struct(filename, **opt):
    verbose = 0

    if 'verbose' in opt and opt['verbose'] != 0:
        verbose = 1

    if verbose:
        sys.stderr.write(f'opt = \n{pformat(opt)}\n')

    with TpCsv(filename, **opt) as tpcsv:
        columns = tpcsv['columns']
        delimiter = tpcsv['delimiter']
        fh = tpcsv['fh']

        num_of_columns = len(columns)
        inconsistent_line_count = 0

        source_list = []

        for attr in ['MatchPattern', 'ExcludePattern']:
            if attr in opt and opt[attr] is not None:
                strings = opt[attr]
            else:
                strings = []

            source_list.append(strings_to_compiled_list(strings, attr))

        source = '\n\n'.join(source_list)

        if verbose:
            sys.stderr.write(f'source code = \n{source}')

        _csv_to_struct_ = load_module('_csv_to_struct_', source)

        array = []

        while 1:
            line = fh.readline()
            if not line:
                break

            line = line.rstrip()

            # https://docs.python.org/2/howto/regex.html
            # match() Determine if the RE matches at the beginning of the string.
            # search() Scan through a string, looking for any location where this RE matches.
            # findall() Find all substrings where the RE matches, and returns them as a list.
            # finditer() Find all substrings where the RE matches, and returns
            # them as an iterator.

            match_patterns = _csv_to_struct_.MatchPattern
            exclude_patterns = _csv_to_struct_.ExcludePattern

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

            cells = line.split(delimiter)

            if len(cells) != num_of_columns:
                inconsistent_line_count += 1

            # zip will throw away any extra columns
            row = dict(zip(columns, cells))

            array.append(row)

        if inconsistent_line_count:
            sys.stderr.write(f'found {inconsistent_line_count},lines having inconsistent number of columns\n')

        ret = {'columns': columns, 'delimiter': delimiter, 'array': array}

        return ret


def main():
    file = 'csv_test.csv'
    struct = csv_to_struct(file)
    print(f'{file} = {pformat(struct)}\n')


if __name__ == '__main__':
    main()


# def query_csv(**opt):
#     if 'verbose' in opt and opt['verbose']:
#         print >> sys.stderr, "opt ="
#         print >> sys.stderr, pformat(opt);
#
#     # import pdb; pdb.set_trace();
#
#     if 'input_type' not in opt:
#         return None
#
#     if opt['input_type'] == 'file':
#         csv_struct = csv_to_struct(opt['input'], **opt)
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
#
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
