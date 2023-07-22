#!/usr/bin/env python

verbose = 1
verbose and print(f'verbose = {verbose}. we should see this line')

verbose = 0
verbose and print(f'verbose = {verbose}. we should not see this line')
