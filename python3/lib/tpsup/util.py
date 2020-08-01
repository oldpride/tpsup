import functools
import inspect
import re
import sys
import traceback
import types
from pprint import pformat
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


def run_module_file(mod_file: str, **opt):
    verbose = opt.get('verbose', 0)

    if mod_file is None:
        if verbose:
            print('mod_file is None. skipped', file=sys.stderr)
            if verbose > 1:
                traceback.print_stack() # default to stderr, set file=sys.stdout for stdout
        return

    with open(mod_file, 'r') as f:
        source = f.read()
        module = None
        try:
            module = load_module(source)
        except Exception:
            traceback.print_stack()  # e.printStackTrace equivalent in python
            module = None

        if module is None:
            sys.stderr.write(f"failed to compile: {mod_file}\n")
            return

        if opt.get('dryrun', False):
            sys.stderr.write(f"dryrun mode: {mod_file} compiled successfully\n")
        else:
            sys.stderr.write(f"running: {mod_file}\n")
            module.run(mod_file=mod_file, **opt)  # pycharm had a warning here. I set to ignore

def silence_BrokenPipeError(func):
    @functools.wraps(func)
    def silenced(*args, **kwargs):
        result = None
        try:
            result = func(*args, **kwargs)
        except BrokenPipeError:
            sys.exit(1)
        return result

    return silenced


def main():
    print(f"not done")


if __name__ == '__main__':
    main()
