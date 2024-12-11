#!/usr/bin/env python

import os
from pprint import pformat

our_cfg = {
    # no need any resources

    # position_args will be inserted into $opt hash to pass forward
    'position_args' : ['env_var'],

    'usage_example' : '''
    - show how python sees an env var. 
      For example, in Windows, PATH and PYTHONPATH are different in bash and Python. 
    
    {{prog}} PATH
    {{prog}} PYTHONPATH
    ''',
}

def code(all_cfg, known, **opt):
    global driver

    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'from code(), known ={pformat(known)}')
        print(f'from code(), opt = {pformat(opt)}')


    env_var = opt['env_var']

    if env_var != 'all':
        value = os.environ[env_var]
        print(f"{env_var}={value}")
    else:
        for key, value in os.environ.items():
            print(f"{key}={value}")
