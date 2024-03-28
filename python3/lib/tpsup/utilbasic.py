
import inspect
import itertools
from pprint import pformat
import re
import functools


def silence_BrokenPipeError(func):
    """replace build-in functions"""

    @functools.wraps(func)
    def silenced(*args, **kwargs):
        result = None
        try:
            result = func(*args, **kwargs)
        except BrokenPipeError:
            sys.exit(1)
        return result

    return silenced


def convert_to_uppercase(h, **opt):
    # convert key or key/value to upper case
    if h is None:
        return h

    if type(h) == str:
        if opt.get("ConvertValue", False):
            return h.upper()
        else:
            return h
    elif type(h) == dict:
        d2 = {}
        for k, v in h.items():
            if opt.get("ConvertKey", False):
                k2 = k.upper()
            else:
                k2 = k

            v2 = convert_to_uppercase(v, **opt)

            d2[k2] = v2
        return d2
    elif type(h) == list:
        l2 = []
        for e in h:
            l2.append(convert_to_uppercase(e, **opt))
        return l2
    else:
        return h


def current_line():
    return inspect.currentframe().f_back.f_lineno


def current_file():
    return inspect.currentframe().f_back.f_code.co_filename

# def __file__():
#     return inspect.currentframe().f_back.f_code.co_filename
#
# the above messed up with tplog()
#
# below are comments
#   File "C:\users\william\sitebase\github\tpsup\python3\lib\tpsup\util.py", line
# 332, in main
#     tplog("hello world")
#   File "C:\users\william\sitebase\github\tpsup\python3\lib\tpsup\util.py", line
# 46, in tplog
#     caller = inspect.stack()[1]
#   File "C:\Program Files\Python3.10\lib\inspect.py", line 1678, in stack
#     return getouterframes(sys._getframe(1), context)
#   File "C:\Program Files\Python3.10\lib\inspect.py", line 1655, in getouterframe
# s
#     frameinfo = (frame,) + getframeinfo(frame, context)
#   File "C:\Program Files\Python3.10\lib\inspect.py", line 1629, in getframeinfo
#     lines, lnum = findsource(frame)
#   File "C:\Program Files\Python3.10\lib\inspect.py", line 952, in findsource
#     module = getmodule(object, file)
#   File "C:\Program Files\Python3.10\lib\inspect.py", line 875, in getmodule
#     f = getabsfile(module)
#   File "C:\Program Files\Python3.10\lib\inspect.py", line 844, in getabsfile
#     _filename = getsourcefile(object) or getfile(object)
#   File "C:\Program Files\Python3.10\lib\inspect.py", line 820, in getsourcefile
#     if any(filename.endswith(s) for s in all_bytecode_suffixes):
#   File "C:\Program Files\Python3.10\lib\inspect.py", line 820, in <genexpr>
#     if any(filename.endswith(s) for s in all_bytecode_suffixes):
# AttributeError: 'function' object has no attribute 'endswith'
#


step_count = 0


def hit_enter_to_continue(initial_steps=0, helper: dict = {}, verbose=0):
    # helper example, see seleniumtools.py
    # helper = {
    #     'd' : ["dump page", dump, {'driver':driver, 'outputdir_dir' : tmpdir} ],
    # }
    global step_count
    if initial_steps:
        step_count = initial_steps

    if step_count > 0:
        step_count -= 1
        if verbose:
            print(f"step_count left={step_count}")
    else:
        hint = f"Hit Enter to continue; a number to skip steps; q to quit"
        for k, v in helper.items():
            hint += f"; {k} to {v[0]}"
        hint += " : "

        answer = input(hint)
        if m := re.match(r"(\d+)", answer):
            # even if only capture 1 group, still add *_; other step_count would become list, not scalar
            step_count_str, *_ = m.groups()
            step_count = int(step_count_str)
        elif m := re.match("([qQ])", answer):
            print("quit")
            quit(0)  # same as exit
        elif helper:  # test dict empty
            matched_helper = False
            for k, v in helper.items():
                if m := re.match(k, answer):
                    func = v[1]
                    args = v[2]
                    func(**args)
                    matched_helper = True
                    break
            if matched_helper:
                # call recursively to get to the hint line
                hit_enter_to_continue(initial_steps, helper)


def print_string_with_line_numer(string: str):
    lines = string.split("\n")
    for (number, line) in enumerate(lines):
        print(f"{number+1:3} {line}")


def arrays_to_hashes(arrays, headers):
    hashes = []
    if not arrays or not headers:
        return hashes

    for aref in arrays:
        href = {}
        for i in range(len(headers)):
            href[headers[i]] = aref[i]
        hashes.append(href)

    return hashes


def hashes_to_arrays(hashes, headers):
    arrays = []
    if not hashes or not headers:
        return arrays

    for href in hashes:
        aref = []
        for header in headers:
            aref.append(href[header])
        arrays.append(aref)

    return arrays


def get_keys_from_array(rows: list, key_name: str, **opt):
    keys = []

    # why it's not called get_keys_from_hash_array()?
    # because it's not just hash in the array.
    # there could be a string in the array, which will default to the hash key.
    #
    # example:
    #
    # rows = [
    #   'orders',
    #  { 'table' : 'trades', 'flag' : 'critical'},
    #  'booking',
    # ]
    #
    # get_keys_from_array(rows, 'table')
    # => ['orders', 'trades', 'booking']
    #

    if not rows:
        return keys

    seen = {}  # python's set internally is a dict

    for row in rows:
        row_type = type(row)

        if row_type is str:
            seen[row] = seen.setdefault(row, 0) + 1
        elif row_type is dict:
            if key_name in row:
                seen[row[key_name]] = seen.setdefault(row[key_name], 0) + 1
            else:
                raise Exception(
                    f"missing key='{key_name}' at row={pformat(row)}")
        else:
            raise Exception(
                f"unsupported type={row_type} at row={pformat(row)}")

    keys = list(seen.keys())

    return keys


def get_node_list(addr, path, **opt):
    # this is like map a data structure to a list of xpath.
    # the data structure is at 'addr'
    # 'path' is the starting point, like '/'
    #
    # below code is converted from perl's get_node_list()
    #
    # addr is a scalar, array or hash (in python: str, int, list, dict)
    # path is a string
    # opt is a hash
    # opt = {
    #    NodeDepth    => 0,
    #    MaxNodeDepth => 100,
    # }
    # return a list in pairs
    #   [
    #     path1, value1,
    #     path2, value2,
    #     ...
    #    ]
    #    path is a string
    #    value is a string, or if MaxNodeDepth is reached, scalar, array or hash
    depth = opt.get("NodeDepth", 0)
    max_depth = opt.get("MaxNodeDepth", 100)

    pairs = []

    if not addr:
        return pairs

    addr_type = type(addr)

    if addr_type is not list and addr_type is not dict:
        pairs.extend([path, addr])
    elif addr_type is list:
        if depth >= max_depth:
            raise Exception(
                f"get_node_list() reached maxdepth {max_depth}")

        i = 0
        for e in addr:
            pairs.extend(get_node_list(addr[i], f"{path}/[{i}]",
                                       **{**opt, 'NodeDepth': depth+1}))
            i += 1
    else:
        # addr_type is dict
        if depth >= max_depth:
            raise Exception(
                f"get_node_list() reached maxdepth {max_depth}")

        for k in sorted(addr.keys()):
            pairs.extend(get_node_list(addr[k], f"{path}/{k}",
                                       **{**opt, 'NodeDepth': depth+1}))

    return pairs


def unify_array_hash(old_array: list, key: str, **opt):
    # old_array = [
    #    'orders',
    #    { 'table' : 'trades', 'flag' : 'critical'},
    #    'booking',
    # ],
    #
    # new_array = unify_array_hash(old_array, 'table');
    #
    # it will look like:
    #
    # new_array = [
    #    { 'table' : 'orders'},
    #    { 'table' : 'trades', 'flag' : 'critical'},
    #    { 'table' : 'booking'},
    # ],

    new_array = []

    if not old_array:
        return new_array

    for row in old_array:
        if type(row) is str:
            new_array.append({key: row})
        elif type(row) is dict:
            if key in row:
                new_array.append(row)
            else:
                raise Exception(
                    f"missing key='{key}' at row={pformat(row)}")
        else:
            raise Exception(
                f"unsupported type={type(row)} at row={pformat(row)}")

    return new_array


def unify_hash_hash(old_dict: dict, default_subkey: str, **opt):
    # old_dict = {
    #    'BOOKID'    : None,
    #    'TRADEID'   : '.+?',
    #    'FILLEDQTY' : {pattern=>'\d+', numeric=>1},
    # },
    #
    # new_dict = unify_hash_hash(old_dict, 'pattern');
    #
    # it will look like:
    #
    # new_dict = {
    #    'BOOKID'    : {pattern=>'BOOKID'},
    #    'TRADEID'   : {pattern=>'.+?'},
    #    'FILLEDQTY' : {pattern=>'\d+', numeric=>1},
    # },

    new_dict = {}

    if not old_dict:

        return new_dict

    for key in old_dict:
        if old_dict[key] is None:
            new_dict[key] = {default_subkey: key}
            continue

        old_type = type(old_dict[key])
        if old_type is str:
            new_dict[key] = {default_subkey: old_dict[key]}
        elif old_type is dict:
            new_dict[key] = old_dict[key]
        else:
            raise Exception(
                f"unsupported type={old_type} at key={key} old_dict={old_dict}")

    return new_dict


def hashes_to_arrays(hashes, headers):
    arrays = []
    if not hashes or not headers:
        return arrays

    for href in hashes:
        aref = []
        for header in headers:
            aref.append(href.get('header', None))
        arrays.append(aref)

    return arrays


def convert_kvlist_to_dict(kvlist: list, **opt):
    # kvlist is a list of key=value
    # example:
    #   kvlist = [
    #       'k1=v1',
    #       'k2=v2',
    #   ]
    #   convert_kvlist_to_dict(kvlist)
    #   => {'k1': 'v1', 'k2': 'v2'}

    dict1 = {}

    if not kvlist:
        return dict1

    for kv in kvlist:
        if m := re.match(r"(\w+)=(.*)", kv):
            k, v = m.groups()
            dict1[k] = v
        else:
            raise Exception(f"bad kv='{kv}'")

    return dict1


def convert_dict_to_kvlist(dict1: dict, **opt):
    # kvlist is a list of key=value
    # example:
    #   dict1 = {
    #       'k1': 'v1',
    #       'k2': 'v2',
    #   }
    #   convert_dict_to_kvlist(dict1)
    #   => [
    #       'k1=v1',
    #       'k2=v2',
    #   ]

    kvlist = []

    if not dict1:
        return kvlist

    for k, v in dict1.items():
        kvlist.append(f"{k}={v}")

    return kvlist


def transpose_lists(lists: list, **opt):
    '''
    https://stackoverflow.com/questions/6473679/transpose-list-of-lists
    '''
    if opt.get("shortest", False):
        # short circuits at shortest nested list if table is jagged:
        return list(map(list, zip(*lists)))
    else:
        # discards no data if jagged and fills short nested lists with None
        return list(map(list, itertools.zip_longest(*lists, fillvalue=None)))


def main():
    # def test_code():
    #     print(__file__)
    #     print(current_file())
    #     print(current_line())
    # import tpsup.exectools
    # tpsup.exectools.test_lines(test_code, globals(), locals())
    # the above did not work
    print(f'__file__ = {__file__}')
    print(f'current_file() = {current_file()}')
    print(f'current_line() = {current_line()}')

    test_objects = [
        {
            'a': 1,
            'b': {
                'c': 2,
                'd': {
                    'e': 3,
                    'f': 4,
                    'g2': ['x1', 'x2', 'x3'],
                },
            },
            'g': [1, 2, 3],
            'h': [
                {'i': 1},
                {'i': 2},
                {'i': 3},
            ],
        },
        [
            'k1', 'v1',
            'k2', 'v2',
        ]
    ]
    for test_object in test_objects:
        print('')
        print('----------------------------------------')
        print(f"test_object = {pformat(test_object)}")
        print(
            f"get_node_list(test_object, '/root') =\n{pformat(get_node_list(test_object, '/root'))}")

    print('')
    print('----------------------------------------')
    test_object = [
        'orders',
        {'table': 'trade', 'flag': 'critical'},
        'booking',
    ]
    print(f"test_object = {pformat(test_object)}")
    print(
        f"get_keys_from_array(test_object, 'table') = {get_keys_from_array(test_object, 'table')}")

    def test_codes():
        transpose_lists([[1, 2, 3], [4, 5, 6], [7, 8, 9]])

    from tpsup.testtools import test_lines
    test_lines(test_codes)


if __name__ == "__main__":
    main()
