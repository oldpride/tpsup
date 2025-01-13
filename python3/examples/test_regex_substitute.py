#!/usr/bin/env python

# string.replae() vs re.sub()
# non-regex vs regex

import pprint
import re

s = "the blue dog and blue cat wore blue hats"

# compiled version
p = re.compile(r"blue (dog|cat)")
s2 = p.sub(r"gray \1", s)
print(s2)
# the gray dog and gray cat wore blue hats

# one-liner
s2 = re.sub(pattern=r"blue (dog|cat)", repl=r"gray \1", string=s)
print(s2)
# the gray dog and gray cat wore blue hats

# named group
p = re.compile(r"blue (?P<animal>dog|cat)")
s2 = p.sub(r"gray \g<animal>", s)
print(s2)
# the gray dog and gray cat wore blue hats

# wild card
s = "/cygdrive/c/Program Files;/cygdrive/c/Users;/cygdrive/d"
p = re.compile(r"/cygdrive/(.)(.*?)(;?)")
s2 = p.sub(r"\1:\2\3", s)
print(s2)
# c:/Program Files;c:/Users;d:

# wild card
s = "a/b/c;d e-f_g,"
p = re.compile("[^a-zA-Z0-9.,_-]")
s2 = p.sub("", s)
print(s2)
# abcde-f_g,
