from pprint import pformat
from typing import Union
import os
import sys

from tpsup.tplog import log_FileFuncLine

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

    if RowType := opt.get('RowType', find_row_type(rows, **opt)):
        if RowType not in [list, dict]:
            raise Exception(
                f"unsupported RowType: {RowType}. can only be list or dict")
    else:
        raise Exception(
            "RowType is not specified and cannot be determined from rows")

    # log_FileFuncLine(f"opt={pformat(opt)}")
    MaxRows = opt.get('MaxRows', len(rows))

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

        if RowType == list:
            headers = rows[0]
            num_headers = len(headers)
            # print(f"headers={headers}", file=sys.stderr)
            for r in rows[1:MaxRows]:
                for j in range(len(r)):
                    if j < num_headers:
                        print(f"{headers[j]:25} '{r[j]}'",
                              file=out_fh)  # padding
                    else:
                        # repeating chars
                        print(f"{' '*25} '{r[j]}'", file=out_fh)
                print(file=out_fh)  # blank line
        else:  # RowType == dict
            for r in rows[:MaxRows-1]:
                for k in sorted(r.keys()):
                    print(f"{k:25} '{r[k]}'", file=out_fh)  # padding
        return

    max_by_pos = []
    MaxColumnWidth = opt.get('MaxColumnWidth', None)
    truncated = 0

    # fix headers of hash (dict), so that we can convert dict to list in a consistent way.
    if RowType == dict:
        headers = find_hashes_keys(rows, **opt)
        # print(f"headers={headers}", file=sys.stderr)

        # for dict, headers is not part of rows, so we handle it separately.
        for k in headers:
            if MaxColumnWidth and len(k) > MaxColumnWidth:
                max_by_pos.append(MaxColumnWidth)
                truncated = 1
            else:
                max_by_pos.append(len(k))

    # find max width for each column
    for r2 in rows[:MaxRows]:
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

    range_start = 0
    range_end = MaxRows
    # exclusive, >>> 'abc'[0:1]
    # 'a'

    if opt.get('RenderHeader', False):
        if RowType == list:
            headers = rows[0]
            range_start = 1
            rang_end = MaxRows + 1
        # else:  # RowType == dict
            # headers = find_hashes_keys(rows) # already done above

        render_one_row(headers, max_by_pos, out_fh, **opt)

        # print the bar right under the header.
        # length will be the bar length, total number of columns.
        # 3 is " | " between columns.
        r_length = 3 * (max_fields - 1)

        for i in range(max_fields):
            r_length += max_by_pos[i]

        print('=' * r_length, file=out_fh)

    for r in rows[range_start:range_end]:
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


def Print_ArrayOfHashes_Vertically(aref: Union[list, None], **opt):
    if not aref:
        return

    headers = None

    if opt.get('headers', None):
        # user-specified headers can be a ref of array or a string
        if isinstance(opt['headers'], list):
            headers = opt['headers']
        elif isinstance(opt['headers'], str):
            headers = opt['headers'].split(',')
        else:
            raise Exception(
                f"unsupported type of headers: {type(opt['headers'])}")

    out_fh = opt.get('out_fh', sys.stdout)

    MaxRows = opt.get('MaxRows', len(aref))

    for r in aref[:MaxRows]:
        if headers is None:
            for k, v in r.items():
                print(f"{k:25} '{v}'", file=out_fh)
        else:
            for c in headers:
                print(f"""{c:25} '{r.get(c,"")}'""", file=out_fh)
        print()


def string_short(obj, top: int = 5, maxlen: int = 200, **opt):
    # print the first top rows of obj
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
    print(f"self detect list or dict: render_arrays(rows, RenderHeader=True)")
    render_arrays(rows, RenderHeader=True)
    print()
    print("--------------------")
    print(f"render_arrays(rows, Vertical=True)")
    render_arrays(rows, Vertical=True)

    rows = [
        {'name': 'tian', 'age': '36'},
        {'name': 'john', 'comment': 'friend of tian'},
    ]
    print()
    print("--------------------")
    print(f"Print_ArrayOfHashes_Vertically(rows)")
    Print_ArrayOfHashes_Vertically(rows)
    print()
    print("--------------------")
    print(f"Print_ArrayOfHashes_Vertically(rows, headers='name,age')")
    Print_ArrayOfHashes_Vertically(rows, headers='name,age')
    print()
    print("--------------------")
    print(f"self detect list or dict: render_arrays(rows, RenderHeader=True)")
    render_arrays(rows, RenderHeader=True)


if __name__ == '__main__':
    main()
