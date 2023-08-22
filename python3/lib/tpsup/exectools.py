import types
import re
from typing import Literal, Union
from tpsup.util import print_string_with_line_numer
from pprint import pformat
from tpsup.tplog import log_FileFuncLine


def _exec_filter(_dict, **opt):
    pattern = opt.get("pattern", None)
    if pattern:
        compiled = re.compile(f"{pattern}")
        return {k: v for k, v in _dict.items() if compiled.match(k)}
    else:
        # return _dict
        compiled_exclude = re.compile(r"_")
        return {k: v for k, v in _dict.items() if not compiled_exclude.match(k)}


def exec_into_globals(_source: str, _globals, _locals, **opt):
    # for variables that won't be passed back to caller, we use _ prefix.
    _verbose = opt.get("verbose", 0)
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
# it is to be overwritten by eval_block().
# it is here to disable the warning from IDE.
def tp_exec_func():
    raise RuntimeError("this function should not be called")


def eval_block(_source: str, _globals, _locals, **opt):
    # _globals and _locals are the caller's globals() and locals()

    verbose = opt.get("verbose", 0)

    if verbose > 1:
        log_FileFuncLine(f"_globals = {pformat(_globals)}")
        log_FileFuncLine(f"_locals = {pformat(_locals)}")
        log_FileFuncLine(f"opt = {pformat(opt)}")

    if "\\" in _source:
        _source = _source.replace("\\", "\\\\")
        log_FileFuncLine(
            f"escaped \\ with \\\\, results in:k _source = \n{_source}")

    # wrap the code block into a function so that eval() a single expression.
    # see above for explanation.
    # add indent
    func_code = shift_indent(correct_indent(_source), shift_space_count=4,)
    if EvalAddReturn := opt.get("EvalAddReturn", False):
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


def correct_indent(source: str, **opt):
    # remove indent.
    # the source my not be correctly indented because it embedded in other
    # code.
    # use the first ident as reference

    verbose = opt.get("verbose", False)
    # verbose = 1

    lines = source.split("\n")

    if verbose:
        print(f"{len(lines)} lines")

    first_indent = None
    compiled_first_indent_search = re.compile(r"^(\s*)\S")
    for i in range(len(lines)):
        # blank lines are ignored
        if m := compiled_first_indent_search.match(lines[i]):
            first_indent, *_ = m.groups()
            length = len(first_indent)
            if verbose:
                print(f"matched first indent {length} chars")
            if length == 0:
                # first line has no ident, then no need to shift left.
                return source
            break
    return shift_indent(source, shift_space_count=-length, **opt)


def shift_indent(source: str, **opt):
    # shift left or right
    shift_tab_count = opt.get("shift_tab_count", 0)
    shift_space_count = opt.get("shift_space_count", shift_tab_count * 4)

    if shift_space_count == 0:
        return source

    lines = source.split("\n")

    for i in range(len(lines)):
        if shift_space_count > 0:
            lines[i] = " " * shift_space_count + lines[i]
        else:
            lines[i] = lines[i][-shift_space_count:]

    return "\n".join(lines)


real_line_pattern = None


def add_return(source: Union[str, list], ReturnLocation: Literal['LastLine', 'LastFront'] = 'LastFront', **opt):
    # this function add a return to the last line of the source code.
    # example, change from
    #     a=1
    #     a+3
    # to
    #     a=1
    #     return a+3
    #
    # LastLine vs LastFront
    # example:
    #     print("hello",      # LastFront
    #          "world")       # LastLine

    source_type = type(source)

    if source_type is list:
        lines = source
    elif source_type is str:
        lines = source.split("\n")
    else:
        raise RuntimeError(f"source type {source_type} not supported")

    global real_line_pattern
    if real_line_pattern is None:
        # non-blank, non-comment line
        real_line_pattern = re.compile(r"^(\s*)([^#\s].*)")

    lastLine = None
    lastFront = None
    minimal_indent = None

    for i in range(len(lines)):
        if m := real_line_pattern.search(lines[i]):
            indent, real_stuff = m.groups()
            if minimal_indent is None:
                minimal_indent = len(indent)
                lastFront = i
            elif len(indent) <= minimal_indent:
                minimal_indent = len(indent)
                lastFront = i
            lastLine = i
    if ReturnLocation == 'LastFront':
        last = lastFront
    else:
        last = lastLine
    if not re.search(r"^\s*return", lines[last]):
        lines[last] = re.sub(r"^(\s*)", r"\1return ", lines[last])

    # return type keep the same as source type.
    if source_type is list:
        return lines
    else:
        return "\n".join(lines)


def test_lines(f: types.FunctionType, source_globals={}, source_locals={}, print_return=True, **opt):
    verbose = opt.get("verbose", 0)
    import inspect
    # we import here because this is a test function.

    source = inspect.getsource(f)
    # get the source code of the function, including comments and blank lines.

    if verbose:
        log_FileFuncLine(f"source = \n{source}")

    if verbose > 1:
        log_FileFuncLine(f"source_globals = \n{pformat(source_globals)}")
        log_FileFuncLine(f"source_locals = \n{pformat(source_locals)}")

    lines = source.split('\n')

    skip_pattern = re.compile(r'^\s*#|^\s*$|^\s*def\s')
    # skip blank lines, comments, and function definition

    lines2 = [l for l in lines if not skip_pattern.match(l)]
    source2 = '\n'.join(lines2)

    if verbose:
        log_FileFuncLine(f"source2 = \n{source2}")

    # align code to the left. this way, we can tell line continuation by checking indent.
    sources3 = correct_indent(source2, **opt)

    if verbose:
        log_FileFuncLine(f"sources3 = \n{sources3}")

    last_line = None
    for line in sources3.split('\n'):
        if line.startswith(' '):  # line.startswith('\s') does not work
            # this is a continuation of last line
            if last_line is None:
                raise RuntimeError(
                    f"line continuation at the beginning of the code")
            last_line = last_line + '\n' + line
            continue

        # now that this line has no indent, therefore, last line is complete.
        if last_line is None:
            # this is the first line
            last_line = line
            continue

        test_1_line(last_line, source_globals, source_locals, **opt)

        last_line = line

    test_1_line(last_line, source_globals, source_locals, **opt)


def test_1_line(line: str, source_globals={}, source_locals={}, print_return=True, print_pformat=True, **opt):
    print()
    print("--------------------")
    print(f"run: {line}")

    combined_globals = {**source_globals, **globals()}
    combined_locals = {**source_locals, **locals()}

    # exec_into_globals(line, combined_globals, combined_locals)
    ret = eval_block(line, combined_globals, combined_locals,
                     **{**opt, 'EvalAddReturn': True})
    if print_return:
        if print_pformat:
            print(f"return with pformat: \n{pformat(ret)}")
        else:
            print(f"return without pformat: \n{ret}")


def main():
    print("test correct_indent()")
    code = """
           
    # a blank line above and a comment
    a = 1
    if a == 2:
        a = 3
    """

    print("--------------------")
    print(code)
    print("--------------------")

    def test_code():
        correct_indent(code, verbose=0)
        shift_indent(code, shift_space_count=4)
        shift_indent(code, shift_space_count=-4)
        shift_indent(code, shift_tab_count=-1)
        print('multiline test', 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, {
              'a': 1, 'b': 2}, [1, 2, 3], {'hello': 'world'})

    test_lines(test_code, globals(), locals(), pformat=0)
    print("--------------------")

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

    test_lines(test_code)

    a = 1
    source = '''
    print("a test line")
    a+1
'''

    print(
        (f'test eval_block(source) = {eval_block(source, globals(), locals())}'))

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
