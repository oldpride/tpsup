import types
import re
from tpsup.util import print_string_with_line_numer
import pprint


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

    _source2 = correct_indent(_source)
    compiled = None
    try:
        # because the code is compiled and passed forward, therefore,
        # there is no file name associated with the code.
        # without a filename, error message's source will be difficult to identify.
        # therefore, we add a filename to the code, passed from caller
        #    opt['source_filename']
        # https://docs.python.org/3/library/functions.html#compile
        # The filename argument should give the file from which the code was read;
        #    pass some recognizable value if it wasn’t read from a file
        source_filename = opt.get("source_filename", "")
        compiled = compile(_source2, source_filename, "exec")
    except Exception as e:
        # note: some errors are run time errors and will not be caught here. for example
        #     NameError: name 'b' is not defined
        # this compile only catches syntax errors
        print_string_with_line_numer(_source2)
        raise e  # reraise the excecption

    try:
        # by default
        #    exec(_source)
        # uses a copy of the caller's locals().
        # However, inside a function, the local scope passed to exec() is actually a copy of the actual
        # local variables; therefore, we force exec() to use the caller's original locals() as below.
        exec(compiled, _globals, _locals)
        # note: the above exec() will take info from _globals and _locals but will not feed back into
        #       _globals, but _locals is affected. note: this is not caller's _locals
    except Exception as e:
        # now we catch the run-time errors
        print_string_with_line_numer(_source2)
        raise e  # reraise the excecption

    # move changes in _locals into _globals because caller's _locals is not modifiable - we only affected
    # the copy of caller's _locals.
    # https://www.pythonpool.com/python-locals/
    # we update _globals and use _globals to pass back the effect to caller
    _updated = _exec_filter(_locals)
    if opt.get("verbose", 0):
        print(f"_updated = {pprint.pformat(_updated)}")
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

# this function should not be called. it is here to disable the warning from IDE.
def tp_exec_func():
    raise RuntimeError("this function should not be called")


def eval_block(_source: str, _globals, _locals, **opt):
    # _globals and _locals are the caller's globals() and locals()

    verbose = opt.get("verbose", 0)

    # wrap the code block into a function so that eval() a single expression.
    # see above for explanation.
    source = f'def tp_exec_func():\n' + shift_indent(correct_indent(_source),
                                                     shift_space_count=4,
                                                     add_return=True,
                                                     )
    if verbose:
        print(f"source = \n{source}")
    exec_into_globals(source, _globals, _locals, **opt)
    return _globals['tp_exec_func']()


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
    real_line_pattern = re.compile(r"^(\s*)[^#\s]")
    last = None
    for i in range(len(lines)):
        if shift_space_count > 0:
            lines[i] = " " * shift_space_count + lines[i]
        else:
            lines[i] = lines[i][-shift_space_count:]
        if real_line_pattern.search(lines[i]):
            last = i
    if opt.get("add_return", False):
        lines[last] = re.sub(r"^(\s*)", r"\1return ", lines[last])

    return "\n".join(lines)


def test_lines(f: types.FunctionType, source_globals={}, source_locals={}, **opt):
    import inspect
    # we import here because this is a test function.

    lines = inspect.getsource(f)
    # get the source code of the function, including comments and blank lines.

    skip_pattern = re.compile(r'^\s*#|^\s*$|^\s*def\s')
    # skip blank lines, comments, and function definition

    for line in lines.split('\n'):
        if skip_pattern.match(line):
            continue
        print(f"run: {line}")

        combined_globals = {**source_globals, **globals()}
        combined_locals = {**source_locals, **locals()}

        exec_into_globals(line, combined_globals, combined_locals)


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
        print(correct_indent(code, verbose=1))
        print(shift_indent(code, shift_space_count=4))
        print(shift_indent(code, shift_space_count=-4))
        print(shift_indent(code, shift_tab_count=-1))

    test_lines(test_code, globals(), locals())
    print("--------------------")

    print("test _updated exec_into_globals()")
    code = """
            a = 1
            if a == 1:
                b = a+1
        """
    exec_into_globals(code, globals(), locals(), verbose=1)

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
    print("here")
    a+1
'''

    print(
        (f'test eval_block(source) = {eval_block(source, globals(), locals())}'))


if __name__ == "__main__":
    main()
