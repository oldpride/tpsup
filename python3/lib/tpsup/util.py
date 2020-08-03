import functools
import inspect
import io
import os
import re
import sys
import traceback
import types
from pprint import pformat
from time import strftime, gmtime
from typing import Dict, List


# https://docs.python.org/3/library/typing.html
# https://stackoverflow.com/questions/38727520/adding-default-parameter-value-with-type-hint-in-python
# type hints: import typing
def string_to_temp_func(string: str, is_exp: int = 0, **opt) -> str:
    """generate a string of expression into a string of function definition"""

    extra_indent = ''
    uncompiled_list = [f'def temp(r):']

    # https://stackoverflow.com/questions/3995034/does-python-re-module-support-word-boundaries-b
    # https://stackoverflow.com/questions/12871066/what-exactly-is-a-raw-string-regex-and-how-can-you-use-it
    if re.search(r'\bifh\b', string):
        # https://stackoverflow.com/questions/713794/catching-an-exception-while-using-a-python-with-statement
        uncompiled_list = uncompiled_list + [
            '    with get_ifh(r["path"]) as (ifh, err):',
            '        if err:',
            '            sys.stderr.write("IOError: " + err + "\\n")',
            '        else:']
        extra_indent = '        '

    # Python makes a big deal between statement (x+=1, print "hell")
    # and expression (x==1, x).
    # "return" cannot only go before expression
    # https://stackoverflow.com/questions/32383788/python-return-s
    # syntax-error
    if is_exp == 1:
        uncompiled_list.append(f"{extra_indent}    return {string}")
    elif is_exp == 0:
        uncompiled_list.append(f"{extra_indent}    {string}")
    else:
        raise Exception(f"unknown is_exp={is_exp}, expect 0/1")

    uncompiled_string = '\n'.join(uncompiled_list)

    if opt.get('verbose'):
        sys.stderr.write(f'uncompiled_string =\n{uncompiled_string}\n')

    return uncompiled_string


def strings_to_funcs(strings: List, funcs_name: str, is_exp: int, **opt) -> str:
    """ convert list of strings into a list of functions"""

    source_list = [f'{funcs_name} = []'] + \
                  [
                      f'{string_to_temp_func(s, is_exp=is_exp, verbose=opt["verbose"])}\n\n{funcs_name}.append(temp)\n'
                      for s in strings]

    funcs = '\n\n'.join(source_list)

    return funcs


def stringdict_to_funcdict(stringdict: Dict[str, str], funcdict_name: str, is_exp: int, **opt) -> str:
    """ convert dictionary of strings into a dictionary of functions"""

    if opt.get('verbose'):
        print(f'stringdict = {pformat(stringdict)}')

    # escape in f string, use double curlies
    # https://stackoverflow.com/questions/42521230/how-to-escape-f-strings-in-python-3-6
    _list = [f'{funcdict_name} = {{}}'] + \
            [
                f'{string_to_temp_func(s, is_exp=is_exp, verbose=opt["verbose"])}\n\n{funcdict_name}["{k}"] = temp\n'
                for k, s in stringdict.items()]

    funcdict = '\n\n'.join(_list)

    return funcdict


def strings_to_compilable_patterns(strings: List, compiled_list_name: str, **opt) -> str:
    """ convert list of strings into a list of (to-be) compilable patterns"""

    statements = [f'{compiled_list_name} = [']
    if strings is not None:
        statements.extend([f'    re.compile("{s}"),' for s in strings])
    statements.extend([f']'])

    return '\n'.join(statements)


def strings_to_compilable_func(strings: List, func_name: str, logic: str = 'and', **opt) -> str:
    """ convert list of strings into ONE compilable function"""

    statements = [f'def {func_name}(r):']

    if logic == 'and':
        if strings is not None:
            statements.extend([f'    if not ({s}): return False' for s in strings])
        statements.append(f'    return True')
    elif logic == 'or':
        if strings is not None:
            statements.extend([f'    if ({s}): return True' for s in strings])
        statements.append(f'    return False')
    else:
        raise RuntimeError(f'unknown logic={logic}')

    return '\n'.join(statements)


# learned from Cookbook with modification from Stackoverflow.
def load_module(source: str, new_module_name=None):
    """ compile the source code into executable using an external module"""
    if new_module_name is None:
        new_module_name = inspect.stack()[1][3]
    # https://stackoverflow.com/questions/32175693/python-importlibs-analogue-for-imp-new-module
    # mod = sys.modules.setdefault(fullname, imp.new_module(fullname))
    mod = sys.modules.setdefault(new_module_name, types.ModuleType(new_module_name))
    code = compile(source, new_module_name, 'exec')
    mod.__file__ = new_module_name
    mod.__package__ = ''
    exec(code, mod.__dict__)
    return mod


def run_module(mod: str, mod_is_file=False, **opt):
    verbose = opt.get('verbose', 0)

    if mod is None:
        if verbose:
            print('mod_file is None. skipped', file=sys.stderr)
            if verbose > 1:
                traceback.print_stack() # default to stderr, set file=sys.stdout for stdout
        return

    if mod_is_file:
        with open(mod, 'r') as f:
            source = f.read()
    else:
        source = mod

    module = None
    try:
        module = load_module(source)
    except Exception:
        traceback.print_stack()  # e.printStackTrace equivalent in python
        module = None

    if module is None:
        sys.stderr.write(f"failed to compile: {mod}\n")
        return

    if opt.get('dryrun', False):
        sys.stderr.write(f"dryrun mode: {mod} compiled successfully\n")
    else:
        sys.stderr.write(f"running: {mod}\n")
        module.run(mod_file=mod, **opt)  # pycharm had a warning here. I set to ignore


def silence_BrokenPipeError(func):
    ''' replace build-in functions'''
    @functools.wraps(func)
    def silenced(*args, **kwargs):
        result = None
        try:
            result = func(*args, **kwargs)
        except BrokenPipeError:
            sys.exit(1)
        return result

    return silenced


def tplog(message:str= None, file=sys.stderr, **opt):
    if message is None:
        message = ''
    timestamp = strftime("%Y-%m-%d %H:%M:%S", gmtime())

    # print(pformat(caller)) *o
    # FrameInfo(frame=<frame object at 0x7f0ce4e87af8>, filename='util.py', lineno=176, function='tplog',
    # code_context=['    caller = inspect.stack()\n'], index=0),
    # FrameInfo(frame=<frame object at 0x7f0ce4a84048>, filename='util.py', lineno=182, function='main',
    # code_context=["    tplog('test')\n"], index=0),
    # FrameInfo(frame=<frame object at 0x12e3428>, filename='util.py', lineno=185, function='<module>',
    # code_context=['    main()\n'], index=0)]
    caller = inspect.stack()[1]

    print(f"{timestamp} {os.path.basename(caller.filename)},{caller.lineno},{caller.function} {message}", file=file, **opt)


def print_exception(e: Exception, stacktrace=True, **opt):
    file = opt.get('file', sys.stderr)

    sio = None
    if file == str:
        # print to string
        sio = io.StringIO()
        file = sio
    if stacktrace:
        print(traceback.format_exc(), file=file)
    else:
        # print("{0}: {1!r}".format(type(e).__name__, e.args), file=file, **opt)
        print("{0}: {1}".format(type(e).__name__, ";".join(e.args)), file=file, **opt)

    if sio:
        string = sio.getvalue()
        sio.close()
        return string

def tplog_exception(e: Exception, **opt):
    tplog(print_exception(e, file=str), **opt)


def main():
    tplog('hello world')

    try:
        raise RuntimeError("test exception")
    except Exception as e:
        print_exception(e)
        tplog(print_exception(e, file=str))


if __name__ == '__main__':
    main()
