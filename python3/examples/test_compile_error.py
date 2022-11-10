#!/usr/bin/env python

pystr = '''
print('abc')
print(abc)
'''
try:
    compile(pystr, '', 'eval')
except Exception as e:

    # print all attributes
    for attr in dir(e):
        print("e.%s = %r" % (attr, getattr(e, attr)))

    #useful attributes:
    print(e.lineno)
    print(e.msg)
    print(e.text)