#!/usr/bin/env python


import inspect


def __line__():
    return inspect.currentframe().f_back.f_lineno


def __file__():
    return inspect.currentframe().f_back.f_code.co_filename


print(f'__file__ = {__file__}')
print(f'__file__() = {__file__()}')
print(f'__line__() = {__line__()}')

# output:
# __file__ = <function __file__ at 0x000001F6DCE375B0>
# __file__() = C:\users\william\sitebase\github\tpsup\python3\examples\test_current_li
# ne_file.py
# __line__() = 17
