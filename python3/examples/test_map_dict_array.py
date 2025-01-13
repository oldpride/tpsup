#!/usr/bin/env python

mydict = {
    "a": 1,
    "b": 2,
    "c": 3,
    "d": 4,
    "e": 5
}

myarray = [mydict[k] for k in ['a', 'b', 'c']]
print(f'myarray={myarray}')
