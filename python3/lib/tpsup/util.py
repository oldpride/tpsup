import functools
import inspect
import io
import os
from pprint import pformat
import re
import sys
import traceback
from time import strftime, gmtime


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


def tplog(message: str = None, file=sys.stderr, prefix: str = "time,caller"):
    if message is None:
        message = ""

    need_prefix = set(prefix.split(","))

    if "time" in need_prefix:
        timestamp_part = f'{strftime("%Y-%m-%d %H:%M:%S", gmtime())} '
    else:
        timestamp_part = ""

    if "caller" in need_prefix:
        # print(pformat(caller)) *o
        # FrameInfo(frame=<frame object at 0x7f0ce4e87af8>, filename='util.py', lineno=176, function='tplog',
        # code_context=['    caller = inspect.stack()\n'], index=0),
        # FrameInfo(frame=<frame object at 0x7f0ce4a84048>, filename='util.py', lineno=182, function='main',
        # code_context=["    tplog('test')\n"], index=0),
        # FrameInfo(frame=<frame object at 0x12e3428>, filename='util.py', lineno=185, function='<module>',
        # code_context=['    main()\n'], index=0)]
        caller = inspect.stack()[1]
        caller_part = (
            f"{os.path.basename(caller.filename)},{caller.lineno},{caller.function} "
        )
    else:
        caller_part = ""

    print(f"{timestamp_part}{caller_part}{message}", file=file)


def print_exception(e: Exception, stacktrace=True, **opt):
    file = opt.get("file", sys.stderr)

    sio = None
    if file == str:
        # print to string
        sio = io.StringIO()
        file = sio
    if stacktrace:
        print(traceback.format_exc(), file=file)
    else:
        # print("{0}: {1!r}".format(type(e).__name__, e.args), file=file, **opt)
        print("{0}: {1}".format(type(e).__name__,
              ";".join(e.args)), file=file, **opt)

    if sio:
        string = sio.getvalue()
        sio.close()
        return string


def tplog_exception(e: Exception, **opt):
    tplog(print_exception(e, file=str), **opt)


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


def get_value_by_key_case_insensitive(value_by_key: dict, key: str, **opt):
    verbose = opt.get("verbose", 0)
    if verbose:
        print(
            f"util.py {current_line()} value_by_key = {pformat(value_by_key)}")

    if not value_by_key:
        return None

    if key in value_by_key:
        return value_by_key[key]

    uc_key = key.upper()

    for k, v in value_by_key.items():
        if uc_key == k.upper():
            return v

    if "default" in opt:
        return opt["default"]
    else:
        raise Exception(
            f"key={key} has no match even if case-insensitive in {value_by_key}")


def get_first_by_key(array_of_hash: list, key: str, **opt):
    if not array_of_hash:
        return None

    CaseSensitive = opt.get("CaseSensitive", False)

    for h in array_of_hash:
        if not h:
            continue

        if CaseSensitive:
            if value := h.get(key, None):
                return value
        else:
            # try case in-sensitive
            v = None
            try:
                v = get_value_by_key_case_insensitive(h, key)
            except Exception as e:
                pass
            if v is not None:
                return v

    return opt.get("default", None)


compiled_scalar_var_pattern = None
compiled_yyyymmdd_pattern = None


def resolve_scalar_var_in_string(clause: str, dict1: dict, **opt):
    # in python, both dict and Dict are reserved words.
    # therefore, we use dict1 instead of dict or Dict.

    # print(f"opt = {opt}")
    verbose = opt.get("verbose", 0)

    if not clause:
        return clause

    if verbose > 1:
        print(f"clause = {clause}")

    global compiled_scalar_var_pattern

    # this is an expensive operation. we only do it once.
    if compiled_scalar_var_pattern is None:
        # scalar_vars is enclosed by double curlies {{...=default}},
        # but exclude {{pattern::...} and {{where::...}}.
        compiled_scalar_var_pattern = re.compile(
            r"{{([0-9a-zA-Z._-]+)(=.{0,200}?)?}}", re.MULTILINE)
        # there are 2 '?':
        #    the 1st '?' is for ungreedy match
        #    the 2nd '?' says the (...) is optional
        # example:
        #    .... {{VAR1=default1}}|{{VAR2=default2}}
        # default can be multi-line
        # default will be undef in the array if not defined.

    vars_defaults = compiled_scalar_var_pattern.findall(clause)

    if verbose:
        print(f"vars_defaults = {vars_defaults}")
        # "{{v1}} and {{v2}} and {{v3=abc}}" => [('v1', ''), ('v2', ''), ('v3', '=abc')]

    defaults_by_var = {}
    scalar_vars = []
    while vars_defaults:
        var, default = vars_defaults.pop(0)
        if default:
            default = default[1:]  # remove the leading '='
        scalar_vars.append(var)
        defaults_by_var.setdefault(var, []).append(default)

    if not scalar_vars:
        return clause  # return when no variable found
    yyyymmdd = get_first_by_key([dict1, opt], 'YYYYMMDD')
    dict2 = {}  # this is a local dict to avoid polluting caller's dict

    if yyyymmdd:
        global compiled_yyyymmdd_pattern
        if compiled_yyyymmdd_pattern is None:
            compiled_yyyymmdd_pattern = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
        if m := compiled_yyyymmdd_pattern.match(yyyymmdd):
            yyyy, mm, dd = m.groups()
            dict2['yyyymmdd'] = yyyymmdd
            dict2['yyyy'] = yyyy
            dict2['mm'] = mm
            dict2['dd'] = dd
        else:
            raise Exception(f"YYYYMMDD='{yyyymmdd}' is in bad format")

    old_clause = clause
    idx_by_var = {}  # this is handle dup var
    for var in scalar_vars:
        if var in idx_by_var:
            idx_by_var[var] += 1
        else:
            idx_by_var[var] = 0
        idx = idx_by_var[var]

        value = None
        try:
            value = get_value_by_key_case_insensitive(
                dict(dict1, **dict2, **opt), var)
        except Exception as e:
            if verbose:
                print(f"cannot resolve var={var} in clause={clause}: {e}")
                print(f"dict1 = {pformat(dict1)}")
            default = defaults_by_var[var][idx] if defaults_by_var[var] else None
            if default is not None:
                verbose and print(f"var={var} default={default}")
                value = default
            else:
                verbose and print(f"var={var} default is undefined.")

        if value is None:
            continue
        # don't do global replacement because dup var may have different default.
        # re.sub(pattern, replacement, string, count, flags)
        # replacement must be a string. use f'{var}' to convert to string.
        # count=0 means replace all matches. default is 0.
        # count=1 means only replace the 1st match
        clause = re.sub(r"\{\{" + var + r"(=.{0,200}?)?\}\}",
                        f'{value}',  # convert value to string
                        clause,
                        count=1,  # only replace the 1st match
                        flags=re.IGNORECASE | re.MULTILINE)
        verbose and print(f"replaced #{idx} {{{var}}} with '{value}'")

    if clause == old_clause:
        return clause  # return when nothing can be resolved.

    # use the following to guard against deadloop
    level = opt.get("level", 0) + 1
    max_level = 10
    if level >= max_level:
        raise Exception(
            f"max_level={max_level} reached when trying to resolve clause={clause}. use verbose mode to debug")

    if opt:
        opt2 = {**opt}
        opt2['level'] = level
    else:
        opt2 = {'level': level}
    # print(f"opt2 = {opt2}")

    # recursive call
    clause = resolve_scalar_var_in_string(clause, dict1, **opt2)

    return clause


def print_string_with_line_numer(string: str):
    lines = string.split("\n")
    for (number, line) in enumerate(lines):
        print(f"{number+1:3} {line}")


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
            aref.append(href[header])
        arrays.append(aref)

    return arrays


def main():
    print("\n------ test tplog")
    tplog("hello world")

    print("\n------ test a short version of tplog")
    tplog("hello world", prefix="time")

    print("\n------ test print_exception")
    try:
        raise RuntimeError("test exception")
    except Exception as e:
        print_exception(e)
        tplog(print_exception(e, file=str))

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

    tests = [
        ('simple {{v1}} and {{v2}} and {{v3=abc}}',
         {'v1': 'hello', 'v2': 1}, 0),
        ('''multi-line {{v1}}
          and {{v2}}
          and {{v3=abc}}
         ''',  # this is a multi-line clause
         {'v1': 'hello', 'v2': 1}, 0),
        ('''dups {{v1}}
            and {{v2=2}}
            and {{v2=3}}
            and {{v3=abc}}
            and {{v3=def}}
          ''',
            {'v1': 'hello', 'v2': 1}, 0),
    ]
    for (clause, dict1, verbose) in tests:
        print('')
        print('----------------------------------------')
        print(f"clause = {clause}, dict1 = {pformat(dict1)}")
        print(
            f"resolved clause = {resolve_scalar_var_in_string(clause, dict1, verbose=verbose)}")

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


if __name__ == "__main__":
    main()
