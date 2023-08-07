import pprint

import inspect
import re
import sys
import traceback
import types
from pprint import pformat
from typing import Dict, List, Union, Callable

from tpsup.tplog import log_FileFuncLine


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
        log_FileFuncLine(f'stringdict = {pformat(stringdict)}')

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
            statements.extend(
                [f'    if not ({s}): return False' for s in strings])
        statements.append(f'    return True')
    elif logic == 'or':
        if strings is not None:
            statements.extend([f'    if ({s}): return True' for s in strings])
        statements.append(f'    return False')
    else:
        raise RuntimeError(f'unknown logic={logic}')

    return '\n'.join(statements)


def load_module(source: Union[str, types.CodeType, types.FunctionType],
                new_module_name=None,
                function_name: str = "default_function", imp: Dict = {}
                ) -> types.ModuleType:
    """
    compile the source code into executable using an external module
        str:  source code
        types.FunctionType: defined function
        types.CodeType: func.__code__
    """
    if new_module_name is None:
        new_module_name = inspect.stack()[1][3]
    # https://stackoverflow.com/questions/32175693/python-importlibs-analogue-for-imp-new-module
    # mod = sys.modules.setdefault(fullname, imp.new_module(fullname))
    mod = sys.modules.setdefault(
        new_module_name, types.ModuleType(new_module_name))

    source_type = type(source)

    # Python variables are scoped to the innermost function, class, or module in which they're assigned. Control
    # blocks like if and while blocks don't count
    if source_type == str:
        # learned from Cookbook
        code = compile(source, new_module_name, 'exec')
    else:
        # create a blank module and we will insert function afterwards
        code = compile("", new_module_name, 'exec')

    mod.__file__ = new_module_name
    mod.__package__ = ''
    mod.__dict__.update(imp)
    # print(f'mod.__dict__ = {pformat(mod.__dict__)}')
    exec(code, mod.__dict__)
    if source_type == types.FunctionType:
        setattr(mod, function_name, source)
    elif source_type == types.CodeType:
        f = types.FunctionType(source, {}, function_name, None, None)
        f.__qualname__ = function_name
    return mod


def run_module(mod: str, mod_type: str = 'string', imp: Dict = {}, **opt):
    verbose = opt.get('verbose', 0)

    if mod is None:
        if verbose:
            print('mod_file is None. skipped', file=sys.stderr)
            if verbose > 1:
                traceback.print_stack()  # default to stderr, set file=sys.stdout for stdout
        return

    if mod_type == 'file':
        with open(mod, 'r') as f:
            source = f.read()
    elif mod_type == 'string':
        source = mod
    else:
        raise RuntimeError(f'unsupported mod_type={mod_type}')

    module = load_module(source, imp=imp)

    if opt.get('dryrun', False):
        sys.stderr.write(f"dryrun mode: {mod} compiled successfully\n")
    else:
        sys.stderr.write(f"running: {mod}\n")
        # pycharm had a warning here. I set to ignore
        return module.run(mod_file=mod, **opt)


def get_non_buildins(dict: Dict):
    ret = {}
    compiled_pattern = re.compile(r'__')
    for k, v in dict.items():
        m = compiled_pattern.match(k)
        if m:
            continue
        ret.update({k: v})
    return ret


def main():
    print('------ test load_module() by source code (str)')
    source = """
def f(n: int) -> int:
    print(f'{n}+1={n+1}')
    return n+1
    
test_dict = {'a': {'b': 1}, 'c': 'hello'}
"""
    mod = load_module(source)
    print(f"{pformat(dir(mod))}")
    mod.f(2)

    def f(n: int) -> int:
        print(f'{n}+1={n+1}')
        return n+1

    print('------ test load_module() by an existing function (types.FunctionType)')
    mod = load_module(f, function_name="f_in_module")
    print(f"{pformat(dir(mod))}")
    mod.f_in_module(2)

    print("------ test load_module() by an existing function's __code__ (types.CodeType)")
    mod = load_module(f.__code__, function_name="f_in_module")
    print(f"{pformat(dir(mod))}")
    mod.f_in_module(2)

    pprint.pprint(mod.test_dict)


if __name__ == '__main__':
    main()
