#!/usr/bin/env python

import pprint
import sys

# in git bash, we i test
#   ./test_argv.py /html
#  sys.argv = ['C:/users/william/sitebase/github/tpsup/python3/examples/test_argv.py', 'C:/Program Files/Git/html']
# how /html is expanded to C:/Program Files/Git/html ??
# answer: https://stackoverflow.com/questions/7250130
# (win10-python3.10) william@tianpc2:/c/users/william/sitebase/github/tpsup/python3/examples$ pathconv check
# enabled
# MSYS2_ARG_CONV_EXCL=
# enabled
# MSYS_NO_PATHCONV=
#
# (win10-python3.10) william@tianpc2:/c/users/william/sitebase/github/tpsup/python3/examples$ python ./test_argv.py /html
# sys.argv = ['./test_argv.py', 'C:/Program Files/Git/html']
#
# (win10-python3.10) william@tianpc2:/c/users/william/sitebase/github/tpsup/python3/examples$ pathconv disable
# MSYS2_ARG_CONV_EXCL=*
# MSYS_NO_PATHCONV=1
#
# (win10-python3.10) william@tianpc2:/c/users/william/sitebase/github/tpsup/python3/examples$ python ./test_argv.py /html
# sys.argv = ['./test_argv.py', '/html']


print(f'sys.argv = {sys.argv}')
