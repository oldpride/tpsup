#!/usr/bin/env python
from pprint import pformat
import time

import tpsup.seleniumtools_old
import tpsup.pstools
import tpsup.env
import os

from selenium import webdriver

our_cfg = {
    "resources": {
        "selenium": {"method": tpsup.seleniumtools_old.get_driver, "cfg": {}},
    },
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
    $ {{prog}} any
    
    """,
}


def code(all_cfg: dict, known: dict, **opt):
    verbose = opt.get("verbose", 0)
    if verbose:
        print(f'from code(), known ={pformat(known)}')
        print(f'from code(), opt = {pformat(opt)}')

    url = f"file:///{tpsup.env.get_native_path(os.environ.get('TPSUP'))}/scripts/tpslnm_test_alert.html"

    driver: webdriver.Chrome = all_cfg["resources"]["selenium"]["driver"]

    actions = [
        [f"url={url}"],
        ['click_xpath=//input[@id="fname"]',
            [f'string=henry', 'tab=1'], 'enter first name'],
        [f"url_accept_alert=http://google.com", 'sleep=1',
            'go to a different site, we should see alert'],
    ]

    print(f"test actions = {pformat(actions)}")

    # '-interactive' is passed through **opt
    result = tpsup.seleniumtools_old.run_actions(driver, actions, **opt)


def post_batch(all_cfg, known, **opt):
    print(f"running post batch")
    driver: webdriver.Chrome = all_cfg["resources"]["selenium"]["driver"]
    driver.quit()
    if tpsup.pstools.prog_running("chrome", printOutput=1):
        print(f"seeing leftover chrome")
