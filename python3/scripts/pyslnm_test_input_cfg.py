#!/usr/bin/env python
from pprint import pformat
import time

import tpsup.seleniumtools
import tpsup.pstools
import tpsup.env
import os

from selenium import webdriver

our_cfg = {
    "resources": {
        "selenium": {"method": tpsup.seleniumtools.get_driver, "cfg": {}},
    },
    'module': 'tpsup.seleniumtools',
    # position_args will be inserted into $opt hash to pass forward
    "position_args": ["host_port"],
    "extra_args": [
        {
            "dest": "headless",
            "default": False,
            "action": "store_true",
            "help": "run in headless mode",
        },
    ],
    "usage_example": """
    - because we need a load static test page, we run everything locally and let chromedriver 
      to start the browser and pick the port.
      the following is tested working in linux, windows cygwin/gitbash/cmd.exe.
    $ {{prog}} auto s=henry
    
    """,
    # all keys in keys, suits and aliases (keys and values) will be converted in uppercase
    # this way so that user can use case-insensitive keys on command line
    "keys": {
        "userid": None,
        "username": None,
        "password": None,
        "dob": None,
    },
    "suits": {
        "henry": {
            "userid": "henry",
            "username": "Henry King",
            "password": "dummy",
            "dob": "11222001",
        },
    },
    "aliases": {"i": "userid", "n": "username", "p": "password"},
    "keychains": {"username": "userid"},
    "show_progress": 1,  # this is only used by lib/tpsup/batch.py

    "opt": {
        # "opt" will be passed into run_batch() and init_resource()

        # "browserArgs": ["window-size=960,540"], # use a small window as this page has no mobile mode.
        # "humanlike": 1, # behave like human, eg, add some random delay
    },
}


def code(all_cfg: dict, known: dict, **opt):
    verbose = opt.get("verbose", 0)
    if verbose:
        print(f'from code(), known ={pformat(known)}')
        print(f'from code(), opt = {pformat(opt)}')

    url = f"file:///{tpsup.env.get_native_path(os.environ.get('TPSUP'))}/scripts/tpslnm_test_input.html"

    driver: webdriver.Chrome = all_cfg["resources"]["selenium"]["driver"]

    actions = [
        [f"url={url}"],
        [
            """
            click_xpath=//input[@id="user id"],
            click_css=#user\ id,
            xpath=//tr[class="non exist"]
         """,
            [
                f'string={known["USERID"]}',
                "code=js_print_debug(driver, element)",
            ],
            "enter user id",
        ],
    ]

    print(f"test actions = {pformat(actions)}")

    # '-interactive' is passed through **opt
    result = tpsup.seleniumtools.run_actions(driver, actions, **opt)

    print(f'active element in current context')
    element = driver.switch_to.active_element
    tpsup.seleniumtools.js_print_debug(driver, element)

    print('')
    print(f'active element in run_actions()')
    element = result['element']
    tpsup.seleniumtools.js_print_debug(driver, element)

    actions2 = [
        [
            "tab=4",
            [
                # test getting element id
                """code=print(f'element id = {element.get_attribute("id")}, expecting DateOfBirth')""",
                """sleep=2""",
            ],
            "go to Date of Birth",
        ],
        [
            "shifttab=3",
            [
                """code=print(f'element id = {element.get_attribute("id")}, expecting password')""",
                f'string={known["PASSWORD"]}',
            ],
            "enter password",
        ],

        [
            'click_xpath=//select[@id="Expertise"]',
            "select=text,JavaScript",
            "select JavaScript",
        ],
        # NOTE: !!!
        # after selection, somehow I have to use xpath to get to the next element, tab
        # won't move to next element.
        # ['tab=2', 'select=value,2', 'select 2-Medium'],
        ['click_xpath=//select[@id="Urgency"]',
            "select=value,2", "select 2-Medium"],
        [None, "code=test_var=2", "set test_var=2"],
        [None, "code=print(f'test_var={test_var}')",
         "print test_var, should be 2"],
        [
            # test searching two elements
            # note: to fit into one string
            # 'xpath=//fieldset/legend[text()="Profile2"]/../input[@class="submit-btn"],xpath=//tr[@class="non exist"]',
            'xpath=//tr[@class="non exist"],xpath=//fieldset/legend[text()="Profile2"]/../input[@class="submit-btn"]',
            ["click", 'gone_xpath=//select[@id="Expertise"]', "sleep=3"],
            "submit",
        ],
    ]
    print(f"test actions2 = {pformat(actions2)}")
    result = tpsup.seleniumtools.run_actions(driver, actions2, **opt)

    # print(f"test result = {pformat(result)}")
    print(f"test result['we_return'] = {result['we_return']}")

    interval = 2
    print(f"sleep {interval} seconds so that you can see")
    time.sleep(interval)
