# these tools are specific to python

import re
from typing import Literal, Union


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


def main():
    from tpsup.testtools import test_lines

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


if __name__ == "__main__":
    main()
