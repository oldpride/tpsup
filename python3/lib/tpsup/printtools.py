from pprint import pformat
from typing import Union
import os
import sys

from tpsup.logtools import log_FileFuncLine

# from perl tpsup/lib/perl/TPSUP/UTIL.pm


def render_one_row(r: list, max_by_pos: list, out_fh, **opt):
    verbose = opt.get('verbose', 0)

    MaxColumnWidth = opt.get('MaxColumnWidth', None)

    num_fields = len(r)
    max_fields = len(max_by_pos)

    truncated = []

    for i in range(max_fields):
        if (MaxColumnWidth is not None) and (max_by_pos[i] > MaxColumnWidth):
            max_len = MaxColumnWidth
        else:
            max_len = max_by_pos[i]

        if i < num_fields and r[i] is not None:
            v = f'{r[i]}'  # convert to string
        else:
            v = ""

        if len(v) > max_len:
            truncated.append(i)
            v2 = v[0:max_len-2] + '..'
        else:
            v2 = v

        buffLen = max_len - len(v2)

        if i == 0:
            print(f"{' ' * buffLen}{v2}", file=out_fh, end='')
        else:
            print(f" | {' ' * buffLen}{v2}", file=out_fh, end='')

    print(file=out_fh)

    if verbose:
        print(f"(truncated at column: {','.join(truncated)})")


def find_row_type(rows: Union[list, None], **opt):
    if not rows:
        return None

    previous_type = None
    max_rows_to_check = opt.get('CheckMaxRows', 100)

    i = 0
    for r in rows[:max_rows_to_check]:
        i += 1
        row_type = type(r)
        if not previous_type:
            previous_type = row_type
            continue
        if previous_type != row_type:
            print(
                f"ERROR: inconsistent row type at row {i}, {row_type} vs {previous_type}")
            return None
    return previous_type


def find_hashes_keys(rows: Union[list, None], **opt):
    if not rows:
        return None

    seen_keys = set()
    max_rows_to_check = opt.get('CheckMaxRows', 100)
    for r in rows[:max_rows_to_check]:
        for k in r.keys():
            seen_keys.add(k)
    return sorted(seen_keys)


def render_arrays(rows: Union[list, None],
                  headers: Union[list, str] = None,
                  verbose=0,
                  Vertical: bool = False,
                  TakeTail=False,
                  RenderHeader=False,
                  MaxRows=None,
                  RowType=None,
                  interactive=False,
                  out_fh=None,
                  **opt):

    # this is in ** because we want to pass it to render_one_row()
    MaxColumnWidth = opt.get('MaxColumnWidth', None)

    if rows is None:
        return

    if len(rows) == 0:
        return

    if out_fh:
        pass
    elif interactive:
        # todo: this is unix only
        cmd = "less -S"
        out_fh = os.popen(cmd, 'w')
    else:
        out_fh = sys.stdout

    if RowType is None:
        RowType = find_row_type(rows, **opt)

    if RowType is None:
        raise Exception(
            "RowType is not specified and cannot be determined from rows")

    if RowType not in [list, dict]:
        raise Exception(
            f"unsupported RowType: {RowType}. can only be list or dict")

    # user-specified headers make code more complicated, but we still need it
    # because csv module (CSV.pm) needs to call this module to print data, and csv
    # module needs to specify headers:
    #    csv module often needs to print a structure of either:
    #       1. headers + a array of arrays of data
    #       2. headers + a array of hashes of data
    #    in the array case, the headers are like the first row of data.
    #    in the hash  case, the headers are used to filter keys of the hashes.
    # Headers' role could get more complicated if want to support other features around them.
    #    But we should keep this part simple.
    #    if users need more features around headers, they can use CSV module to pre-process
    #       the data, and then use this module to print the data.
    #    For example, if user wanted to specify headers to filter array of arrays, it should
    #       convert the array of arrays to array of hashes first, using CSV module, and then
    #       filter the keys.
    # outside csv module, we rarely need user-specified headers. but we will
    # keep the behavior consistent with csv module.
    # summary:
    #    If $rows is array of arrays,
    #       if user specified headers, we prepend it to the rows, making it the first row.
    #       if user didn't specify headers,
    #           if user wanted to render headers, we use the first row as headers.
    #           if user didn't want to render headers, we print rows without headers.
    #    If $rows is array of hashes,
    #       if user specified headers, we use it to filter out unwanted keys.
    #       if user didn't specify headers, we use all keys as headers.

    min_start_row = 0
    if headers is not None:
        if isinstance(headers, str):
            headers = headers.split(',')
        elif isinstance(headers, list):
            pass
        else:
            raise Exception(
                f"unsupported type of headers: {type(headers)}")
    elif RenderHeader or RowType == dict or Vertical:
        if RowType == list:
            # if user want to render header but didn't specify headers, we use the first row as headers.
            min_start_row = 1
            headers = rows[0]
        else:  # RowType == dict
            headers = find_hashes_keys(rows, **opt)

    if MaxRows:
        if MaxRows > len(rows):
            MaxRows = len(rows)
    else:
        MaxRows = len(rows)

    if Vertical and RowType == list and len(rows) < 2:
        # when vertically print the arrays, we need at least 2 rows, with first row being as the header
        return

    start_row = min_start_row

    if TakeTail:
        if len(rows) - MaxRows > min_start_row:
            start_row = len(rows) - MaxRows

    if Vertical:
        if RowType == list:
            num_headers = len(headers)
            # print(f"headers={headers}", file=sys.stderr)
            for r in rows[start_row:MaxRows]:
                for j in range(len(r)):
                    if j < num_headers:
                        print(f"{headers[j]:25} '{r[j]}'",
                              file=out_fh)  # padding
                    else:
                        # repeating chars
                        print(f"{' '*25} '{r[j]}'", file=out_fh)
                print(file=out_fh)  # blank line
        else:  # RowType == dict
            for r in rows[:MaxRows]:
                for k in headers:
                    print(f"""{k:25} '{r.get(k, '')}'""",
                          file=out_fh)  # padding
                print(file=out_fh)
        return

    max_by_pos = []
    truncated = 0

    if headers:
        for k in headers:
            if MaxColumnWidth and len(k) > MaxColumnWidth:
                max_by_pos.append(MaxColumnWidth)
                truncated = 1
            else:
                max_by_pos.append(len(k))

    # find max width for each column
    for r2 in rows[start_row:start_row+MaxRows]:
        if RowType == list:
            r = r2
        else:  # RowType == dict
            r = [r2.get(k, "") for k in headers]

        for i in range(len(r)):
            i_length = len(f'{r[i]}')

            # check whether an index in a list
            # if not i in max_by_pos:  # this doesn't work
            # the following works!
            if i >= len(max_by_pos):
                # max_by_pos[i] = length # IndexError: list assignment index out of range
                if MaxColumnWidth and i_length > MaxColumnWidth:
                    i_length = MaxColumnWidth
                    truncated = 1
                max_by_pos.append(i_length)
            elif max_by_pos[i] < i_length:
                if MaxColumnWidth and i_length > MaxColumnWidth:
                    i_length = MaxColumnWidth
                    truncated = 1
                max_by_pos[i] = i_length

    if verbose:
        print(f"max_by_pos={max_by_pos}", file=sys.stderr)

    max_fields = len(max_by_pos)

    # note:
    # python's range_end is exclusive while perl's range_end is inclusive
    # $ python
    # >>> 'abc'[0:1]
    # 'a'
    # $ perl -e '@a=split(//,"abc"); print @a[0..1], "\n";'
    # ab

    if RenderHeader:
        render_one_row(headers, max_by_pos, out_fh, **opt)

        # print the bar right under the header.
        # length will be the bar length, total number of columns.
        # 3 is " | " between columns.
        r_length = 3 * (max_fields - 1)

        for i in range(max_fields):
            r_length += max_by_pos[i]

        print('=' * r_length, file=out_fh)

    for r in rows[start_row:start_row+MaxRows]:
        if RowType == dict:
            array = [r.get(k, "") for k in headers]
        else:  # RowType == list
            array = r
        render_one_row(array, max_by_pos, out_fh, **opt)

    if out_fh != sys.stdout:
        # if out_fh is from caller, then don't close it. let caller close it.
        if not opt.get('out_fh', None):
            out_fh.close()

    if truncated:
        print(
            f"some columns were truncated to MaxColumnWidth={MaxColumnWidth}", file=sys.stderr)


def string_short(obj, top: int = 5, maxlen: int = 200, **opt):
    # print the first top rows of obj
    # used by pttrace.py
    if isinstance(obj, list):
        rows = obj
    elif isinstance(obj, str):
        rows = obj.splitlines()
    else:
        return pformat(obj)

    rows2 = []
    for r in rows[:top]:
        if isinstance(r, str):
            if len(r) > maxlen:
                r = r[0:maxlen] + f'..(truncated at {maxlen}'
            rows2.append(r)
        else:
            rows2.append(pformat(r))

    if len(rows) > top:
        rows2.append(
            f"(total {len(rows)} lines, only show the first {top} lines)")

    return '\n'.join(rows2)


def print_short(obj, desc: str = '', **opt):
    print(f"{desc}={string_short(obj, **opt)}")


def main():
    rows1 = [
        ['name', 'age'],
        ['tian', '36'],
        ['olenstroff', '40', 'will discuss later'],
        ['john', '30'],
        ['mary'],
    ]

    rows2 = [
        {'name': 'tian', 'age': '36'},
        {'name': 'john', 'comment': 'friend of tian'},
    ]

    def test_codes():
        find_row_type(rows1)
        render_arrays(rows1)
        render_arrays(rows1, MaxColumnWidth=10, RenderHeader=True)
        render_arrays(rows1, MaxColumnWidth=10, RenderHeader=True, headers='name')
        render_arrays(rows1, MaxColumnWidth=10, Vertical=True)
        render_arrays(rows1, Vertical=True, headers='name')
        render_arrays(rows1, RenderHeader=1, MaxRows=2)
        render_arrays(rows1, RenderHeader=1, MaxRows=2, TakeTail=True)

        find_row_type(rows2)
        find_hashes_keys(rows2)
        render_arrays(rows2)
        render_arrays(rows2, RenderHeader=True)
        render_arrays(rows2, RenderHeader=True, headers='name')
        render_arrays(rows2, Vertical=True)
        render_arrays(rows2, Vertical=True, headers='name,age')

    from tpsup.exectools import test_lines
    test_lines(test_codes, source_globals=globals(), source_locals=locals())


if __name__ == '__main__':
    main()
