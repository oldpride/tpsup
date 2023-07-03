#!/usr/bin/env python

import pprint
import sys

# in git bash, we i test
#   ./test_argv.py /html
#  sys.argv = ['C:/users/william/sitebase/github/tpsup/python3/examples/test_argv.py', 'C:/Program Files/Git/html']
# how /html is expanded to C:/Program Files/Git/html is a mystery to me.??

print(f'sys.argv = {sys.argv}')
