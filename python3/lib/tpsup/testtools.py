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

    if verbose > 1:
        log_FileFuncLine(f"source = \n{source}")

    if verbose > 1:
        log_FileFuncLine(f"source_globals = \n{pformat(source_globals)}")
        log_FileFuncLine(f"source_locals = \n{pformat(source_locals)}")

    lines = source.split('\n')

    # skip_pattern = re.compile(r'^\s*#|^\s*$|^\s*def\s')
    # skip blank lines, comments, and function definition
    skip_pattern = re.compile(r'^\s*#|^\s*$')

    def_pattern = re.compile(r'^\s*def\s')
    if def_pattern.match(lines[0]):
        # skip the first line if it is a function definition
        verbose > 1 and log_FileFuncLine(f"skip the first line: {lines[0]}")
        lines = lines[1:]

    if verbose > 1:
        lines_string = '\n'.join(lines)
        log_FileFuncLine(f"lines = \n{lines_string}")

    # align code to the left. this way, we can tell line continuation by checking indent.
    lines2 = correct_indent(lines, **opt)

    if verbose > 1:
        lines2_string = '\n'.join(lines2)
        log_FileFuncLine(f"lines2 = \n{lines2_string}")

    in_test = False  # whether in "#TEST_BEGIN" and "#TEST_END" block
    test_code = []
    i = -1
    for line in lines2:
        i += 1
        if not in_test:
            if line.startswith('#TEST_BEGIN') or line.startswith('# TEST_BEGIN'):
                in_test = True
            else:
                if skip_pattern.match(line):
                    continue

                # line.startswith('\s') does not work because \s is a regex.
                # but startswith only takes a string.
                if line.startswith(' '):
                    # indent means continuation of last line
                    # check whether test_code is empty
                    if not test_code:
                        raise RuntimeError(
                            f"unexpected indent at the beginning of the code")
                    test_code.append(line)
                    continue
                else:
                    # not in test and not a blank line
                    # this is a normal line, a start line of a new test
                    # we need to run the last test in test_code
                    if test_code:
                        # convert test_code to a string
                        test_code_string = '\n'.join(test_code)
                        run_1_test(test_code_string, source_globals, source_locals, **opt)
                        test_code = []
                    test_code.append(line)
        else:
            # in_test
            if line.startswith('#TEST_END') or line.startswith('# TEST_END'):
                in_test = False
                if test_code:
                    # convert test_code to a string
                    test_code_string = '\n'.join(test_code)
                    run_1_test(test_code_string, source_globals, source_locals, **opt)
                    test_code = []
            else:
                test_code.append(line)

    if test_code:
        # run the last test in test_code
        # convert test_code to a string
        test_code_string = '\n'.join(test_code)
        run_1_test(test_code_string, source_globals, source_locals, **opt)


def run_1_test(test_string: str, source_globals={}, source_locals={}, print_return=True, print_pformat=True, **opt):
    print()
    print("--------------------")
    print(f"run: {test_string}")

    combined_globals = {**source_globals, **globals()}
    combined_locals = {**source_locals, **locals()}

    # exec_into_globals(line, combined_globals, combined_locals)
    ret = eval_block(test_string, combined_globals, combined_locals,
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

        # TEST_BEGIN
        a2 = 1
        b2 = 2
        a2+b2 == 3
        # TEST_END

        # TEST_BEGIN
        a3 = 'hello'
        b3 = 'world'
        a3+b3 == 'helloworld'
        # TEST_END

    test_lines(test_codes, source_globals=locals(), source_locals=locals())


if __name__ == "__main__":
    main()
