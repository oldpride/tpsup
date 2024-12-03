#!/usr/bin/env python
from pprint import pformat
import time

import tpsup.seleniumtools
import tpsup.pstools
import tpsup.envtools
import os

from selenium import webdriver
import tpsup.envtools

our_cfg = {

    'module': 'tpsup.seleniumtools',
    # position_args will be inserted into $opt hash to pass forward
    # "position_args": ["host_port"],

    "usage_example": """
    - because we need a load static test page, we run everything locally and let chromedriver 
      to start the browser and pick the port.
      the following is tested working in linux, windows cygwin/gitbash/cmd.exe.
    $ {{prog}} s=henry
    
    
    Three ways to run the browser

    1. let selenium to start a local browser automatically. like above example.

    2. start Chrome (c1) on localhost with debug port 9222.
    From Linux,
        /usr/bin/chromium-browser --no-sandbox --disable-dev-shm-usage --window-size=960,540 \
        --user-data-dir=~/chrome_test --remote-debugging-port=9222 
        or 
        /opt/google/chrome/chrome --no-sandbox --disable-dev-shm-usage --window-size=960,540 \
        --user-data-dir=~/chrome_test --remote-debugging-port=9222
    From Cygwin or GitBash,
        "C:/Users/$USERNAME/sitebase/Windows/10.0/Chrome/Application/chrome.exe" --window-size=960,540 \
        --user-data-dir=C:/users/$USERNAME/chrome_test --remote-debugging-port=9222

    From cmd.exe, (have to use double quotes)
        "C:/Users/$USERNAME/sitebase/Windows/10.0/Chrome/Application/chrome.exe" --window-size=960,540 \
        --user-data-dir=C:/users/%USERNAME%/chrome_test --remote-debugging-port=9222

   {prog} -hp localhost:9222 s=henry

   3. start Chrome (c1) on remote PC with debug port 9222.

    +------------------+       +---------------------+
    | +---------+      |       |  +---------------+  |
    | |selenium |      |       |  |chrome browser |------->internet
    | +---+-----+      |       |  +----+----------+  |
    |     |            |       |       ^             |
    |     |            |       |       |             |
    |     v            |       |       |             |
    | +---+---------+  |       |  +----+---+         |
    | |chromedriver |------------>|netpipe |         |
    | +-------------+  |       |  +--------+         |
    |                  |       |                     |
    |                  |       |                     |
    |  Linux           |       |   PC                |
    |                  |       |                     |
    +------------------+       +---------------------+

    PC> "C:/Users/%USERNAME%/Chrome/Application/chrome.exe" \
    --remote-debugging-port=9222 --user-data-dir=%USERPROFILE%\\ChromeTest
    on the same remote PC, launch cygwin, in cygwin term: netpipe 9333 localhost:9222
   {prog} -hp remote_PC:9333 s=-henry

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
            "dob": "01222023",
        },
    },
    "aliases": {"i": "userid", "n": "username", "p": "password"},
    "keychains": {"username": "userid"},
    "show_progress": 1,  # this is only used by lib/tpsup/batch.py

    "opt": {
        # "opt" will be passed into run_batch() and init_resource()

        # "browserArgs": ["window-size=960,540"], # use a small window as this page has no mobile mode.
    },
}


def code(all_cfg: dict, known: dict, **opt):
    verbose = opt.get("verbose", 0)
    if verbose:
        print(f'from code(), known ={pformat(known)}')
        print(f'from code(), opt = {pformat(opt)}')

    url = f"file:///{tpsup.envtools.get_native_path(os.environ.get('TPSUP'))}/scripts/tpslnm_test_input.html"

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
                f'string={known["DOB"]}',
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
