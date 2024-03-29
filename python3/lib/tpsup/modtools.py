import pprint

import inspect
import re
import sys
import traceback
import types
from pprint import pformat
from typing import Dict, List, Union, Callable

from tpsup.logbasic import log_FileFuncLine


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
                new_module_name: str = None,
                function_name: str = "default_function",
                imp: dict = None,  # import attr
                existing_module: types.ModuleType = None,  # add code to an existing module
                **opt
                ) -> types.ModuleType:
    """
    compile the source code into executable using an external module
        str:  source code
        types.FunctionType: defined function
        types.CodeType: func.__code__
    """
    verbose = opt.get('verbose', 0)
    if existing_module:
        mod = existing_module

        if verbose:
            log_FileFuncLine(f'mod = {pformat(dir(mod))}')
        # new_module_name = mod.__spec__.origin
        new_module_name = mod.__name__
        if verbose:
            log_FileFuncLine(f'new_module_name = {new_module_name}')
    else:
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
    if imp is not None:
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


compiled_by_source = {}


def compile_code(source: str,
                 is_exp=False,
                 signature: str = "",
                 **opt):

    if (not source in compiled_by_source):
        # randomize the function name to avoid conflict
        from random import randint
        rand = randint(0, 9999)

        mod_source = f'def _exp{rand}({signature}):\n'
        if is_exp:
            mod_source += f'    return {source}\n'
        else:
            mod_source += f'    {source}\n'
            # mod_source += f'    return True\n'

        exp_module = load_module(mod_source)

        compiled = getattr(exp_module, f'_exp{rand}')
        compiled_by_source[source] = compiled

    return compiled_by_source[source]


def compile_codedict(sourcedict: dict,
                     is_exp=False,
                     code_header: str = None,
                     signature: str = "",
                     **opt):
    '''
    compile a dict of source strings into a module,
    using the dict key as function name
    '''
    mod_source = ''
    for k, source in sourcedict.items():
        mod_source += f'def {k}({signature}):\n'
        if is_exp:
            mod_source += f'    return {source}\n'
        else:
            mod_source += f'    {source}\n'
            # mod_source += f'    return True\n'
        mod_source += f''

    if mod_source != '':
        exp_module = load_module(mod_source)
    else:
        exp_module = None

    retdict = {}
    for k in sourcedict.keys():
        retdict[k] = getattr(exp_module, k)

    return retdict


def compile_codelist(sourcelist: list,
                     is_exp=False,
                     code_header: str = None,
                     signature: str = "",
                     **opt):
    '''
    compile a list of source strings into a module,
    code header can be some import or other pre-defined code
    example:
        code_header = 'import re'

    signature is the function signature, example:
        signature = "r, verbose=0"
    '''
    verbose = opt.get('verbose', 0)

    compiledlist = []

    if len(sourcelist) == 0:
        return compiledlist

    if code_header is not None:
        mod_source = code_header
    else:
        mod_source = ''

    # randomize the function name to avoid conflict
    from random import randint
    rand = randint(0, 9999)
    for i in range(0, len(sourcelist)):
        mod_source += f'def _exp{rand}_{i}({signature}):\n'

        if is_exp:
            mod_source += f'    return {sourcelist[i]}\n'
        else:
            mod_source += f'    {sourcelist[i]}\n'
            # mod_source += f'    return True\n'
        mod_source += f''

    if verbose:
        log_FileFuncLine(f'mod_source = \n{mod_source}')

    exp_module = load_module(mod_source, **opt)

    for i in range(0, len(sourcelist)):
        compiled_func = getattr(exp_module, f'_exp{rand}_{i}')
        compiledlist.append(compiled_func)

    return compiledlist


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

    print()
    print("------------------------------------------------")
    source = "r['a'] == 1"
    print(f'source = {source}')
    compiled_func = compile_code(source, is_exp=True, signature="r")
    r = {'a': 1, 'b': 2}
    print(f'compiled_func({r}) = {compiled_func(r)}')

    print()
    print("------------------------------------------------")
    sourcelist = ['r["a"] == 1', 'r["b"] == 2']
    compiledlist = compile_codelist(sourcelist, is_exp=True, signature="r")
    print(f'sourcelist = {pformat(sourcelist)}')
    r2 = {'a': 1, 'b': 2}
    r3 = {'a': 1, 'b': 3}
    for compiled_func in compiledlist:
        print(f'compiled_func({r2}) = {compiled_func(r2)}')
        print(f'compiled_func({r3}) = {compiled_func(r3)}')

    print()
    print("------------------------------------------------")
    sourcedict = {'exp1': 'r["a"] == 1', 'exp2': 'r["b"] == 2'}
    compileddict = compile_codedict(sourcedict, is_exp=True, signature="r")
    print(f'sourcedict = {pformat(sourcedict)}')
    r2 = {'a': 1, 'b': 2}
    r3 = {'a': 1, 'b': 3}
    for k, exp in compileddict.items():
        print(f'{k}({r2}) = {exp(r2)}')
        print(f'{k}({r3}) = {exp(r3)}')

    print()
    print("------------------------------------------------")
    print("test injecting code into existing module")
    mod_source = """
from pprint import pformat
r = {}

def export_r(r2):
    global r
    r = r2

def dump_r():
    global r
    print(f'inside dump_r(), r = {pformat(r)}')
"""

    mod = load_module(mod_source)

    mod_source2 = """
def new_func():
    dump_r()
"""

    load_module(mod_source2, existing_module=mod)
    print(f"export works")
    export_r = getattr(mod, 'export_r')
    export_r({'a': 1, 'b': 2})
    dump_r = getattr(mod, 'dump_r')
    dump_r()
    new_func = getattr(mod, 'new_func')
    new_func()
    r = getattr(mod, 'r')
    r2 = {'c': 3, 'd': 4}
    print(f"directly assign doesn't work")
    r = r2
    new_func()
    print(f"clear+update works")
    r = getattr(mod, 'r')
    r.clear()
    new_func()
    r.update(r2)
    new_func()


if __name__ == '__main__':
    main()
