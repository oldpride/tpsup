#!/usr/bin/env python3

import pprint

dict1 = {}

dict2 = {'a': 1, 'b': 2}

dict1['c'] = dict2

print('before, dict1 = ')

pprint.pprint(dict1)

dict2['a'] = 3

print('after, dict1 = ')

pprint.pprint(dict1)

