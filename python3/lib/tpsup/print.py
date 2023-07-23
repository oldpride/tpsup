from typing import Union
import os
import sys

# from perl tpsup/lib/perl/TPSUP/UTIL.pm


def render_one_row(r: list, max_by_pos: list, out_fh, **opt):
    verbose = opt.get('verbose', 0)

    MaxColumnWidth = opt.get('MaxColumnWidth', None)

    num_fields = len(r)
    max_fields = len(max_by_pos)

    truncated = []

    for i in range(max_fields):
        if (MaxColumnWidth is not None) and (max_by_pos[i] > MaxColumnWidth):
            max = MaxColumnWidth
        else:
            max = max_by_pos[i]

        if i < num_fields and r[i] is not None:
            v = f'{r[i]}'  # convert to string
        else:
            v = ""

        if len(v) > max:
            truncated.append(i)
            v2 = v[0:max-2] + '..'
        else:
            v2 = v

        buffLen = max - len(v2)

        if i == 0:
            print(f"{' ' * buffLen}{v2}", file=out_fh, end='')
        else:
            print(f" | {' ' * buffLen}{v2}", file=out_fh, end='')

    print(file=out_fh)

    if verbose:
        print(f"(truncated at column: {','.join(truncated)})")


def render_arrays(rows: Union[list, None], **opt):
    verbose = opt.get('verbose', 0)

    if rows is None:
        return

    if len(rows) == 0:
        return

    out_fh = None
    if opt.get('interactive', False):
        # todo: this is unix only
        cmd = "less -S"
        out_fh = os.popen(cmd, 'w')
    elif opt.get('out_fh', None):
        out_fh = opt['out_fh']
    else:
        out_fh = sys.stdout

    if opt.get('Vertical', False):
        # when vertically print the arrays, we need at least 2 rows, with the first
        # as the header
        #    name: tian
        #     age: 36
        #
        #    name: john
        #     age: 30
        if len(rows) < 2:
            return

        headers = rows[0]
        num_headers = len(headers)
        # print(f"headers={headers}", file=sys.stderr)

        for i in range(1, len(rows)):
            r = rows[i]
            for j in range(len(r)):
                if j < num_headers:
                    print(f"{headers[j]:25} '{r[j]}'", file=out_fh)  # padding
                else:
                    print(f"{' '*25} '{r[j]}'", file=out_fh)  # repeating chars
            print(file=out_fh)  # blank line
        return

    max_by_pos = []

    for r in rows:
        for i in range(len(r)):
            length = len(r[i])

            # check whether an index in a list
            # if not i in max_by_pos:  # this doesn't work
            # the following works!
            if i >= len(max_by_pos):
                # max_by_pos[i] = length # IndexError: list assignment index out of range
                max_by_pos.append(length)
            elif max_by_pos[i] < length:
                max_by_pos[i] = length

    if verbose:
        print(f"max_by_pos={max_by_pos}", file=sys.stderr)

    max_fields = len(max_by_pos)

    MaxColumnWidth = opt.get('MaxColumnWidth', None)

    range_start = 0
    if opt.get('RenderHeader', False):
        r = rows[0]
        range_start = 1

        render_one_row(r, max_by_pos, out_fh, **opt)

        # print the bar right under the header.
        # length will be the bar length, total number of columns.
        # 3 is " | " between columns.
        length = 3 * (max_fields - 1)

        for i in range(max_fields):
            if MaxColumnWidth is not None and max_by_pos[i] > MaxColumnWidth:
                max = MaxColumnWidth
            else:
                max = max_by_pos[i]

            length += max

        print('=' * length, file=out_fh)

    for r in rows[range_start:]:
        render_one_row(r, max_by_pos, out_fh, **opt)

    if out_fh != sys.stdout:
        # if out_fh is from caller, then don't close it. let caller close it.
        if not opt.get('out_fh', None):
            out_fh.close()

    if MaxColumnWidth is not None:
        truncated = 0
        for i in range(max_fields):
            if MaxColumnWidth > max_by_pos[i]:
                truncated += 1
                break
        if truncated:
            print(
                f"{truncated} columns were truncated to MaxColumnWidth={MaxColumnWidth}", file=sys.stderr)


def main():
    print()
    print("--------------------")
    print("test render_arrays()")
    rows = [
        ['name', 'age'],
        ['tian', '36'],
        ['olenstroff', '40', 'will discuss later'],
        ['john', '30'],
        ['mary'],
    ]
    print(f"render_arrays(rows)")
    render_arrays(rows)
    print()
    print("--------------------")
    print(f"render_arrays(rows, RenderHeader=True)")
    render_arrays(rows, RenderHeader=True)
    print()
    print("--------------------")
    print(f"render_arrays(rows, Vertical=True)")
    render_arrays(rows, Vertical=True)


if __name__ == '__main__':
    main()
