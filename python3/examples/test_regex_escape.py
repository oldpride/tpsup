#!/usr/bin/env python


import pprint
import re

s = "my request leve (P3)"

p = re.compile("\(p([1-5])\)", re.IGNORECASE)
if m := p.search(s):
    print("matched")
    pprint.pprint(m.groups())
