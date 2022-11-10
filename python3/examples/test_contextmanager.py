#!/usr/bin/env python3

# https://blog.usejournal.com/trinity-of-context-managers-generators-decorators-4809a991c76b


class FileContextManager:
    def __init__(self, filePath, mode):
        print('Init called')
        self.__filePath = filePath
        self.__mode = mode

    def __enter__(self):
        print('Enter called, attempting to open File')
        self.__f = open(self.__filePath, self.__mode)
        return self.__f

    def __exit__(self, *args):
        self.__f.close()
        print('Exit called and File closed')

# we test passing the context managed object (f below) to outside the context management

outside_f = None

with FileContextManager('test_kwargs_dict.py', 'r') as f:
    outside_f = f
    print('Inside context manager')
    # for line in f:
    #     print(line)
    print(next(f))

print(f'outside_f = {outside_f}')
for line in outside_f:
    print(line)

# output
#
# Init called
# Enter called, attempting to open File
# Inside context manager
# def change_kwargs(**kwargs):
#
# Exit called and File closed
# outside_f = <_io.TextIOWrapper name='test_kwargs_dict.py' mode='r' encoding='UTF-8'>
# Traceback (most recent call last):
#   File "./test_contextmanager.py", line 33, in <module>
#     for line in outside_f:
# ValueError: I/O operation on closed file.

