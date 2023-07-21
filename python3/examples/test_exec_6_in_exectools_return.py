#!/usr/bin/env python
import os
import tpsup.exectools
from pprint import pformat

# eval() vs exec()
#    eval() returns a value. can only handle a single expression.
#    exec() does not return a value. can handle a code block.
# dilemma:
#    we want to exec() a code block,
#    but we also want to get a return value.
# solution:
#    put the code block into a function, and then eval() the function


def eval_block_simple(source, **opt):
    # return tpsup.exectools.eval_block(source, **opt)
    return tpsup.exectools.eval_block(source, globals(), locals(), **opt)


a = 1

source = '''
print(f'a={a}')
a+1
'''


print(
    f'eval_block_simple(source)= {eval_block_simple(source, verbose=1)}')
