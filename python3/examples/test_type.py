#!/usr/bin/env python

# https://stackoverflow.com/questions/72121231/python-when-local-variable-uses-a-build-in-function-name

for type, path in [('dir', 'c:/users')]:
    print(f'{type}={path}')

mystring = 'this string'

if type(mystring) == str:
    print(mystring)