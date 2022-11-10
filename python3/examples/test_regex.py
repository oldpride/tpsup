#!/usr/bin/env python3

import pprint
import re

line = b'11=ABC123,35=D,54=1'

# pattern = rb'\b35=[0-9a-zA-Z]{1,2}([^.0-9B-Z]{1,2})\d'
# pattern = rb'35=([0-9a-zA-Z])'
pattern = rb'(?P<delimiter>[^0-9a-zB-Z]{1,2})\d+=[^=]+?(?P=delimiter)'
# pattern = r'(?P<delimiter>[,])\d+=[^=]+?(?P=delimiter)'
compiled = re.compile(pattern)

m = compiled.search(line)

if m:
    pprint.pprint(m.group('delimiter'))
