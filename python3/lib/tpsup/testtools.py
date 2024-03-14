from pprint import pformat
import re
import types
from tpsup.exectools import eval_block
from tpsup.logbasic import log_FileFuncLine
from tpsup.pythontools import correct_indent


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
    a = 1
    b = "hello"
    array1 = [[1, 2, 3], [4, 5, 6], ]

    def test_codes():
        a + 1
        b
        array1

        {'key1': 1, 'key2': [3, 4]}

        1+1 == 2

        1 in [1.0, 2]
        "a" in ["a", "b"]
        "a" in ["b", "c"]

        [1, 2] == [1.0, 2]
        {a: -1, b: 2} == {b: 2, a: -1.0}

    test_lines(test_codes, source_globals=locals(), source_locals=locals())


if __name__ == "__main__":
    main()
