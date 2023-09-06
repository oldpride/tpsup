#!/usr/bin/env python
import datetime
import os
import time
from typing import Union

import tpsup.env

import tpsup.csvtools
import tpsup.htmltools
import tpsup.seleniumtools_old
import tpsup.pstools
from pprint import pformat


our_cfg = {
    # position_args will be inserted into $opt hash to pass forward
    'position_args': ['action'],

    'usage_example': f'''
    {{{{prog}}}} check
    ''',
}


def code(all_cfg, known, **opt):
    global driver

    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'from code(), known ={pformat(known)}')
        print(f'from code(), opt = {pformat(opt)}')

    action = opt.get('action')

    result = tpsup.seleniumtools_old.check_setup(compareVersion=1)
