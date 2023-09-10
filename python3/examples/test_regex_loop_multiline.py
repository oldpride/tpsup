#!/usr/bin/env python

import re
from pprint import pformat


string = '''xpath=//input[@id="user id"],
            css=#user\ id,
            xpath=//tr[class="non exist"]
         '''

locator_compiled_path1 = re.compile(r'(?:\n|\r\n|\s?)*(css|xpath)=(.+)', re.MULTILINE|re.DOTALL)
locator_compiled_path2 = re.compile(r'(.+?)(?:\n|\r\n|\s?)*,(?:\n|\r\n|\s?)*(css|xpath)=', re.MULTILINE|re.DOTALL)

if m1:=locator_compiled_path1.match(string):
    type, path_string = m1.groups()
    print(f'extracted {type}, {path_string}')

    type_paths = []

    while m2:=locator_compiled_path2.match(path_string):
        path, type2 = m2.groups()
        type_paths.append([type, path])
        print(f'added {type}, {path}')

        type = type2

        pos = m2.end()
        path_string = path_string[pos:]

    type_paths.append([type, path_string])
    print(f'at last added {type}, {path_string}')

    print(f'{pformat(type_paths)}')