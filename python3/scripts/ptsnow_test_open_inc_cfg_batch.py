#!/usr/bin/env python

from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from pprint import pformat
import tpsup.seleniumtools
import tpsup.pstools
import tpsup.envtools

our_cfg = {

    'resources': {
        'selenium': {
            'method': tpsup.seleniumtools.get_driver,
            'cfg': {}
        },
    },

    'extra_args': [
        {'dest': 'headless', 'default': False,
            'action': 'store_true', 'help': 'run in headless mode'},
    ],

    'usage_example': '''
    - run everything locally and let chromedriver to start the browser and pick the port
    {{prog}} s=user
    {{prog}} -b %USERPROFILE%/snow_inc.txt
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

    driver = all_cfg['resources']['selenium']['driver']
    actions = [
        ['url=copy the new-incident url here; make sure it loads the iframes too'],
        ['xpath=//iframe[@name="gsft_main"]', 'frame', 'go to main frame'],
        ['click_xpath=//div[@id="AC.incident.caller_id"]',
            ['clear_attr=value', f"string={known['MYNAME']}",],
            'enter caller name'
         ],

        ['tab=1',
         [
             # it took a while for snow validate, until done, it will display "Invalid reference"
             'gone_xpath=//div[text()="Invalid reference"]',

             # we can input string but string changes often. so stay with index is safer
             # "string=$known->{CATEGORY}",
             "select=index,1",
         ],
         'enter category'
         ],

        [
            # somehow, tab to next element doesn't work from a select element. so we use xpath
            # 'tab=1',
            'click_xpath=//select[@id="sys_display.subcategory"]',

            # again, selet index is more stable than input string
            # "string=$known->{SUBCATEGORY}",
            "select=index,1",
            'enter subcategory'
        ],
        [
            # again, tab to next element doesn't work from a select element. so we use xpath
            # 'tab=1',
            'click_xpath=//input[@id="sys_display.incident.business_service"]',
            f"string={known['SERVICE']}",
            'enter Service'
        ],

        ['tab=1',
         [
             'gone_xpath=//div[text()="Invalid reference"]',
             f"string={known['CI']}",
         ],
         'configuration item'
         ],

        ['tab=1', f"string={known['EXTERNAL']}", 'external client affected'],

        ['tab=5', f"select=value,{known['IMPACT']}", 'enter impact'],

        [
            # again, tab to next element doesn't work from a select element. so we use xpath
            'click_xpath=//select[@id="incident.urgency"]',
            f"select=value,{known['URGENCY']}",
            'enter urgency'
        ],

        [
            # again, tab to next element doesn't work from a select element. so we use xpath
            'click_xpath=//input[@id="sys_display.incident.assignment_group"]',
            f"string={known['ASSIGNGROUP']}",
            'assignment group'
        ],
        [
            'tab=1',
            [
                # it took a long time for snow validate, until done, it will display "Invalid reference"
                'gone_xpath=//div[text()="Invalid reference"]',
                f"string={known['ASSIGNTO']}",
            ],
            'enter assigned to'
        ],

        # put (self-closable) at front because short description field can be truncated.
        # substr
        ['tab=1',
            f"string=(self-closable) {known['DETAIL']}"[0:200], 'short desc'],

        ['tab=1', f"string={known['DETAIL']}", 'detail desc'],
        ['xpath=//button[@id="sysverb_insert_bottom"]', 'click', 'click to submit'],
        ['xpath=//a[starts-with(@aria-label, "Open record: INC")]',
         '', 'verify'],
    ]

    print(f'actions = {pformat(actions)}')

    # make sure pass along **opt, which has flogs: -interactive, -show_progress, ...
    tpsup.seleniumtools.run_actions(driver, actions, **opt)


def post_batch(all_cfg, known, **opt):
    print(f'running post batch')
    driver = all_cfg['resources']['selenium']['driver']
    driver.quit()
    if tpsup.pstools.prog_running('chrome', printOutput=1):
        print(f"seeing leftover chrome")
