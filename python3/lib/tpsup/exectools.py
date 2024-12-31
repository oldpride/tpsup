import types
import re
from typing import Literal, Union
from tpsup.pythontools import add_return, correct_indent, shift_indent
from tpsup.utilbasic import print_string_with_line_numer
from pprint import pformat
from tpsup.logbasic import log_FileFuncLine


def multiline_eval(expr,
                   _globals=None,
                   _locals=None,
                   **opt):
    '''
    Evaluate several lines of input, returning the result of the last line
    https://stackoverflow.com/questions/12698028

    eval() can only handle a single expression, not a code block (multiple expressions).
    '''
    _verbose = opt.get("verbose", 0)

    if (_globals is None) or (_locals is None):
        import inspect
        if _globals is None:
            _globals = inspect.currentframe().f_back.f_globals
        if _locals is None:
            _locals = inspect.currentframe().f_back.f_locals

    import ast
    _tree = ast.parse(expr)
    _body_but_last = _tree.body[:-1]
    _last_expr = _tree.body[-1]
    
    if _verbose > 1:
        print(f"last_expr = {ast.dump(_last_expr)}")
    
    _eval_expr = ast.Expression(_last_expr.value)
    _exec_expr = ast.Module(_body_but_last, 
                            type_ignores=[], # this is required by python 3.8. Later version may not need this.
                            
                            )
    exec(compile(_exec_expr, 'file', 'exec'), _globals, _locals)
    _result = eval(compile(_eval_expr, 'file', 'eval'), _globals, _locals)

    _updated = _exec_filter(_locals)
    if _verbose > 1:
        log_FileFuncLine(f"_updated = {pformat(_updated)}")
    _globals.update(_updated)

    return _result

def _exec_filter(_dict, **opt):
    pattern = opt.get("pattern", None)
    if pattern:
        return {k: v for k, v in _dict.items() if re.match(f"{pattern}", k)}
    else:
        # return _dict
        return {k: v for k, v in _dict.items() if not re.match(r"_", k)}


def exec_into_globals(_source: str,
                      # _globals and _locals are default to the caller's globals() and locals()
                      # use {} to start with empty.
                      _globals=None,
                      _locals=None,
                      **opt):
    # for variables that won't be passed back to caller, we use _ prefix.
    _verbose = opt.get("verbose", 0)

    if (_globals is None) or (_locals is None):
        import inspect
        if _globals is None:
            _globals = inspect.currentframe().f_back.f_globals
        if _locals is None:
            _locals = inspect.currentframe().f_back.f_locals

    if BeginCode := opt.get("BeginCode", None):
        _source2 = BeginCode + "\n" + correct_indent(_source)
    else:
        _source2 = correct_indent(_source)

    if _verbose > 1:
        log_FileFuncLine(f"after corrected indent, _source2 = \n{_source2}")

    _compiled = None
    try:
        # because the code is compiled and passed forward, therefore,
        # there is no file name associated with the code.
        # without a filename, error message's source will be difficult to identify.
        # therefore, we add a filename to the code, passed from caller
        #    opt['source_filename']
        # https://docs.python.org/3/library/functions.html#compile
        # The filename argument should give the file from which the code was read;
        #    pass some recognizable value if it wasn’t read from a file
        _source_filename = opt.get("source_filename", "dynamic code")
        _compiled = compile(_source2, _source_filename, "exec")
    except Exception as e:
        # note: some errors are run time errors and will not be caught here. for example
        #     NameError: name 'b' is not defined
        # this compile only catches syntax errors
        print_string_with_line_numer(_source2)
        raise e  # reraise the excecption

    if opt.get("compile_only", False):
        return _compiled

    try:
        # by default
        #    exec(_source)
        # uses a copy of the caller's locals().
        # However, inside a function, the local scope passed to exec() is actually a copy of the actual
        # local variables; therefore, we force exec() to use the caller's original locals() as below.
        exec(_compiled, _globals, _locals)
        # note: the above exec() will take info from _globals and _locals but will not feed back into
        #       _globals, but _locals is affected. note: this is not caller's _locals
    except Exception as _e:
        # now we catch the run-time errors
        print_string_with_line_numer(_source2)
        raise _e  # reraise the excecption

    # move changes in _locals into _globals because caller's _locals is not modifiable - we only affected
    # the copy of caller's _locals.
    # https://www.pythonpool.com/python-locals/
    # we update _globals and use _globals to pass back the effect to caller
    _updated = _exec_filter(_locals)
    if _verbose > 1:
        log_FileFuncLine(f"_updated = {pformat(_updated)}")
    _globals.update(_updated)

    # key point: python's globals()'s scope to 1 file.
    # If multiple files involved, for example, we call exectools.exec_into_globals from a
    # different module, which is called by another module, we can either
    #    - use a dedicated namespace to keep the effect, eg, use tpsup.globals.
    #    - keep all the effects in one file's globals,
    #      eg, user program may call tpsup.seleniumtools to exec() code, we keep all effects
    #      in tpsup.seleniumtools namespace (its globals()). and then use
    #         getattr(tpsup.seleniumtools, 'we_return') to retrieve the value from caller.


# eval() can handle a single expression
#     >>> eval("1+2")
#     3
#
# eval() cannot handle a code block
#     >>> a='''
#     ... b=1
#     ... c=b+1
#     ... c==3
#     ... '''
#     >>> eval(a)
#     Traceback (most recent call last):
#     File "<stdin>", line 1, in <module>
#     File "<string>", line 2
#         b=1
#         ^
#     SyntaxError: invalid syntax
#
# put code block into a function so that eval() a single expression.
#
#     >>> def f():
#     ...     b=1
#     ...     c=b+1
#     ...     return c==3
#     ...
#     >>> eval("f()")
#     False

# this function should not be called.
# it is to be overwritten inside eval_block().
# it is here to disable the warning from IDE.
def tp_exec_func():
    raise RuntimeError("this function should not be called")


def eval_block(_source: str, _globals=None, _locals=None, **opt):
    # _globals and _locals default to the caller's globals() and locals()

    verbose = opt.get("verbose", 0)

    if verbose > 1:
        log_FileFuncLine(f"_globals = {pformat(_globals)}")
        log_FileFuncLine(f"_locals = {pformat(_locals)}")
        log_FileFuncLine(f"opt = {pformat(opt)}")

    if (_globals is None) or (_locals is None):
        import inspect
        if _globals is None:
            _globals = inspect.currentframe().f_back.f_globals
        if _locals is None:
            _locals = inspect.currentframe().f_back.f_locals

    if "\\" in _source:
        # example: r'C:\Program Files\Python38\lib\site-packages\tpsup\exectools.py'

        # check whether this is a raw string.
        # if raw, we don't need to escape the backslash
        # if not raw, we need to escape the backslash
        if not re.search(r"r'[^']*\\|r\"[^\"]*\\", _source):
            _source = _source.replace("\\", "\\\\")
            log_FileFuncLine(
                f"escaped \\ with \\\\, results _source = \n{_source}")

    # wrap the code block into a function so that eval() a single expression.
    # see above for explanation.
    # add indent
    func_code = shift_indent(correct_indent(_source), shift_space_count=4,)
    if opt.get("EvalAddReturn", False):
        func_code = add_return(func_code, **opt)
    _source2 = f'def tp_exec_func():\n{func_code}'
    if verbose:
        print(f"_source2 = \n{_source2}")
    exec_into_globals(_source2, _globals, _locals, **opt)
    _ret = None
    try:
        _ret = _globals['tp_exec_func']()
        return _ret
    except Exception as e:
        print()
        print_string_with_line_numer(_source2)
        print()
        raise e


def test_compile(_source: str, _globals, _locals, **opt):
    _ret = exec_into_globals(_source, _globals, _locals, compile_only=1, **opt)
    return _ret


def main():
    from tpsup.testtools import test_lines

    print("test _updated exec_into_globals()")
    code = """
            a = 1
            if a == 1:
                b = a+1
        """
    exec_into_globals(code, globals(), locals(), verbose=0)

    print("--------------------")

    print("test error handling in exec_into_globals()")
    code = """
        a = 1
        if c == 2: # c was not defined
            a = c
    """
    try:
        exec_into_globals(code, globals(), locals())
    except Exception as e:
        print(f"caught exception: {e}")
    print("--------------------")
    print("we should see an exception above")

    print("")

    # keep test code in a function so that IDE can check syntax

    def test_code():
        # we can have comment and blank lines in the test code

        print("hello world")
        multiline_eval("a=2;1/a")

    test_lines(test_code)

    a = 1
    source = '''
    print("a test line")
    a+1
'''

    print(
        (f'test eval_block(source) = {eval_block(source, globals(), locals())}'))

    # the downside of using array instead of function to manage test codes
    # is missing syntax check.
    test_codes = [
        # the following will pass compile():
        'print(f"test unknown var {unknown_var}")',  # undefined var
        '1+1',  # expression
        'junk',  # unknown statement

        # the following will fail compile():
        '''
        print("hello world")
                print("wrong indent")''',  # wrong indent
        '"hello',     # missing quote
        '99 === 99',    # wrong operator
    ]

    for t in test_codes:
        print()
        print("--------------------")
        try:
            print(
                f"compile('''{t}''') = {test_compile(t, globals(), locals())}")
        except Exception as e:
            print(f"compile('''{t}'''): {e}")


if __name__ == "__main__":
    main()
