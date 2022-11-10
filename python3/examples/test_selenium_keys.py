#!/usr/bin/env python

from selenium.webdriver.common.keys import Keys
from pprint import pformat

# selenium.webdriver.common.keys.Keys have no get method.
# class Keys(object):
#     """
#     Set of special keys codes.
#     """
#
#     NULL = '\ue000'
#     CANCEL = '\ue001'  # ^break
#     HELP = '\ue002'
#     BACKSPACE = '\ue003'
#     BACK_SPACE = BACKSPACE

# print(Keys['TAB'])
print(f'null="{pformat(Keys.__getattribute__(Keys, "NULL"))}"')
print(f'enter="{Keys.__getattribute__(Keys, "ENTER")}"')
print(f'tab = "{Keys.__getattribute__(Keys, "TAB")}"')
print(f'abcBACKSPACE="abc{Keys.__getattribute__(Keys, "BACKSPACE")}"')
print(f'not_found="{Keys.__getattribute__(Keys, "not_found")}"')