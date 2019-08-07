import gzip
import re
import os
import time

# https://stackoverflow.com/questions/17809386/how-to-convert-a-
# stat-output-to-a-unix-permissions-string
# python 3.3 and above has stat.filemode() to do this
import sys
from contextlib import contextmanager

now = time.time()


def permissions_to_unix_name(r):
    is_dir = 'd' if r['type'] == 'dir' else '-'
    dic = {'7': 'rwx', '6': 'rw-', '5': 'r-x', '4': 'r--',
           '3': '-wx', '2': '-w-', '1': '--x', '0': '---'}
    perm = str(oct(r['mode'])[-3:])
    return is_dir + ''.join(dic.get(x, x) for x in perm)


def ls(r):
    # https://realpython.com/python-string-formatting/
    print(
        f'{permissions_to_unix_name(r)} {r["nlink"]:>2} {r["owner"]:>8} {r["group"]:>8} {r["size"]:>9} {r["mtime_local"]} {r["path"]}')


# https://stackoverflow.com/questions/713794/catching-an-exception-while-using-a-python-with-statement
@contextmanager
def get_ifh(filename: str):
    # https://stackoverflow.com/questions/2489669/function-parameter-types-in-python
    try:
        if filename.endswith('.gz'):
            ifh = gzip.open(filename, 'rb')
        else:
            ifh = open(filename, 'rb')
    except IOError as err:
        yield None, err
    else:
        try:
            yield ifh, None
        finally:
            ifh.close()

# the rest
