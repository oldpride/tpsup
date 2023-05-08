#!/usr/bin/env python
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from pprint import pformat
import time

import tpsup.seleniumtools_old
import tpsup.pstools
import tpsup.env

our_cfg = {
    'resources': {
        'selenium': {
            'method': tpsup.seleniumtools_old.get_driver,
            'cfg': {}
        },
    },

    # position_args will be inserted into $opt hash to pass forward
    'position_args': ['host_port'],

    'extra_args': [
        {'dest': 'headless', 'default': False,
            'action': 'store_true', 'help': 'run in headless mode'},
    ],

    'usage_example': '''
    - run everything locally and let chromedriver to start the browser and pick the port
    linux1$ {{prog}} auto s=henry
    
    - connect to a local browser at a port. 
    if the browser is not up, chromedriver will start a browser at that port.
    linux1$ {{prog}} localhost:9222 s=henry
    
    - start Chrome (c1) on remote PC with debug port 9222.

    +------------------+       +---------------------+
    | +---------+      |       |  +---------------+  |
    | |selenium |      |       |  |chrome browser +------->internet
    | +---+-----+      |       |  +----+----------+  |
    |     |            |       |       ^             |
    |     |            |       |       |             |
    |     v            |       |       |             |
    | +---+---------+  |       |  +----+---+         |
    | |chromedriver +------------>+netpipe |         |
    | +-------------+  |       |  +--------+         |
    |                  |       |                     |
    |                  |       |                     |
    |  Linux           |       |   PC                |
    |                  |       |                     |
    +------------------+       +---------------------+

   # prepare test
   cygwin$ win_chrome_netpipe -allow linux1

   linux1$ {{prog}} 192.168.1.179:9333 i=jane n="Jane Queen" p=dummy, dob=09222014
   linux1$ {{prog}} 192.168.1.179:9333 s=henry p=dummy2
   linux1$ {{prog}} 192.168.1.179:9333 -batch tpslnm_test_batch.txt
   
   # on windows gitbash and cygwin, the same way
   gitbash$ {{prog}} auto s=henry p=dummy2
   cygwin$ {{prog}} auto s=henry p=dummy2
    ''',

    # all keys in keys, suits and aliases (keys and values) will be converted in uppercase
    # this way so that user can use case-insensitive keys on command line
    'keys': {
        'userid': None,
        'username': None,
        'password': None,
        'dob': None,
    },

    'suits': {
        'henry': {
            'userid': 'henry',
            'username': 'Henry King',
            'password': 'dummy',
            'dob': '11222001',
        },
    },

    'aliases': {
        'i': 'userid',
        'n': 'username',
        'p': 'password'
    },

    'keychains': {
        'username': 'userid'
    }
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
        # ['url=https://google.com', 'tab=5'],
        ['url=https://google.com'],
        ['xpath=//input[@name="q"]', 'string=perl selenium'],
        [None, 'key=enter,1'],
    ]

    print(f'test actions = {pformat(actions)}')

    tpsup.seleniumtools_old.run_actions(driver, actions)

    for tag_a in driver.find_elements(by=By.TAG_NAME, value='a'):
        link = None
        try:
            url = tag_a.get_attribute('href')
        # except NoSuchElementException as e:
        except NoSuchElementException:
            pass
        else:
            # print(f'url={url}')
            print(f'hostname = {urlparse(url).hostname}')


def post_batch(all_cfg, known, **opt):
    print(f'running post batch')
    driver = all_cfg['resources']['selenium']['driver']
    driver.quit()
    if tpsup.pstools.prog_running('chrome', printOutput=1):
        print(f"seeing leftover chrome")
