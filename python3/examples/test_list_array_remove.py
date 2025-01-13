#!/usr/bin/env python3

'''
remove a element from list by value
'''

from pprint import pformat


a = ['a', 'b', 'c', 'd']
print(f'a={pformat(a)}')
a.remove('c')
print(f'after removed c, a={pformat(a)}')
a.remove('e')
print(f'after removed e, a={pformat(a)}')
