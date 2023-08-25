#!/usr/bin/env python
from pprint import pformat
import time

import tpsup.seleniumtools
import tpsup.pstools
import tpsup.env
import os

from selenium import webdriver

our_cfg = {
    "module": "tpsup.seleniumtools",

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

    url = f"file:///{os.path.normpath(os.environ.get('TPSUP'))}/scripts/tpslnm_test_alert.html"

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
    result = tpsup.seleniumtools.run_actions(driver, actions, **opt)
