#!/usr/bin/env python

from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from pprint import pformat
import tpsup.dummytools
import tpsup.pstools
import tpsup.envtools

our_cfg = {
    'module': 'tpsup.dummytools',

    'position_args': ['host_port'],

    'extra_args': {
        'dummyarg1': {'switches': ['-da1', '-dummyarg1'], 'default': False,
                      'action': 'store_true', 'help': 'dummyarg1 in cfg.py'},
        'dummyarg3': {'switches': ['-da3', '-dummyarg3'], 'default': False,
                      'action': 'store_true', 'help': 'dummyarg3 in cfg.py'},

        # overwrite 'record' arg to set default to 'detail'.
        'record': {'switches': ['--record'],
                   'default': 'detail',
                   'action': 'store',
                   'help': 'record keys (separated by comma) to avoid run twice. default: detail'},

        # extra_args's key 'show_progress' overwrite our_cfg's 'show_progress'.
        # we need explicity set the default to None,
        #    so that it will default to our_cfg's 'show_progress'.
        # (action=store_false's default is True, not None.)
        # the complete waterfall is:
        #    extra_args -> our_cfg -> module.py -> batch.py
        # also the destination of the value goes the extra_args's key 'show_progress'. therefore,
        # we can name the swiches libraly, here we used '-hide_progress'.
        'show_progress': {'switches': ['-hide_progress'],
                          'default': None,  # this effectively default to our_cfg's show_progress
                          'action': 'store_false',  # overwrite our_cfg's show_progress=1
                          'help': 'disable show_progess'},
    },

    'usage_example': '''
    - this test script doesn't run selenium at all. it just shows how to use cfg.
    {{prog}} auto s=user
    {{prog}} auto any
    {{prog}} auto -b ptbatch_test_batch.txt

    - run again to test record log
    {{prog}} auto -b ptbatch_test_batch.txt

    - compare show_progress value
    {{prog}} auto -b ptbatch_test_batch.txt --record ""
    {{prog}} auto -b ptbatch_test_batch.txt --record "" -hide_progress
    ''',

    # all keys in keys, suits and aliases (keys and values) will be converted in uppercase
    # this way so that user can use case-insensitive keys on command line
    'keys': {
        'MYNAME': tpsup.envtools.get_user_firstlast(),
        'CATEGORY': 'Technology Processing',
        'SUBCATEGORY': 'User Complaint',
        'SERVICE': 'Trade Plant',
        'CI': None,
        'EXTERNAL': 'N',
        'IMPACT': 3,
        'URGENCY': 3,
        'ASSIGNGROUP': 'TradePlantSupport',
        'ASSIGNTO': None,
        'SHORT': 'User reported Trade Plant issue',
        'DETAIL': None,
    },

    'suits': {
        'USER': {
            'CATEGORY': 'Technology Processing',
            'SUBCATEGORY': 'User Complaint',
            'SHORT': 'User reported Trade Plant issue',
        },

        'DATA': {
            'CATEGORY': 'Data Integrity',
            'SUBCATEGORY': 'Incorrect Data',
            'SHORT': 'Incorrect Data in TradePlant',
        },

        'PROC': {
            'CATEGORY': 'Technology Faults',
            'SUBCATEGORY': 'Unexpected Behavior',
            'SHORT': 'Trade Plant Process failed',
        },

        'AUTOSYS': {
            'CATEGORY': 'Technology Faults',
            'SUBCATEGORY': 'Unexpected Behavior',
            'SHORT': 'Trade Plant Process failed',
        },
    },

    'aliases': {
        'SH': 'SHORT',
        'D': 'DETAIL',
        'I': 'IMPACT',
        'U': 'URGENCY',
        'E': 'EXTERNAL',
        'N': 'MYNAME',
    },

    'keychains': {
        # keychains are used to generate a key from other keys. won't cause dead loop.
        'DETAIL': 'SHORT',
        'SHORT': 'DETAIL',
        'ASSIGNTO': 'MYNAME',  # default to self-assigned
        'CI': 'SERVICE',
    },

    'show_progress': 1,
    # "batch_cutoff": 'today',    # midnight
    # "batch_cutoff": '20300101', # future
    # 'batch_cutoff': 'today-06', # 6 am

    # where to put the setting?
    # - settings outside 'opt' are normally used by batch.py's general logic, eg, run_batch().
    # - settings inside 'opt' are normally used by *_cfg.py's code() function;
    #   so are command line args.
    #   use 'opt' if there is a chance that you want to move the setting to command line,
    #       because this way you don't need to change the batch.py's general logic which
    #       is likely shared by many scripts.
    'opt': {
        # "opt" are optional switches, to be passed into *_cfg.py's code() function's **opt.
    }
}


def code(all_cfg, known, **opt):
    # **opt combines all_cfg['opt'] and command line args.
    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'''
from code(), known =
{pformat(known)}

from code(), opt =
{pformat(opt)}

''')

    print(f"show_progress = {all_cfg['show_progress']}")
