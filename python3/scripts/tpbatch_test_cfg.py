#!/usr/bin/env python

from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from pprint import pformat
import tpsup.seleniumtools
import tpsup.pstools
import tpsup.env

our_cfg = {

    'resources': {
        'selenium': {
            'method': tpsup.seleniumtools.get_driver,
            'cfg': {},
            "init_resource": 0,
        },
    },

    'position_args': ['host_port'],

    'extra_args': [
        {'dest': 'headless', 'default': False,
            'action': 'store_true', 'help': 'run in headless mode'},
    ],

    'usage_example': '''
    - run everything locally and let chromedriver to start the browser and pick the port
    {{prog}} auto s=user
    {{prog}} auto -b tpbatch_test_batch.txt
    ''',

    # all keys in keys, suits and aliases (keys and values) will be converted in uppercase
    # this way so that user can use case-insensitive keys on command line
    'keys': {
        'MYNAME': 'John Smith',
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
        'DETAIL': 'SHORT',
        'SHORT': 'DETAIL',
        'ASSIGNTO': 'MYNAME',  # default to self-assigned
        'CI': 'SERVICE',
    },

    'show_progress': 1,
}


def code(all_cfg, known, **opt):
    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'''
from code(), known =
{pformat(known)}

from code(), opt =
{pformat(opt)}

''')
