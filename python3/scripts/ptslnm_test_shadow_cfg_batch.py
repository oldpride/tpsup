#!/usr/bin/env python
from pprint import pformat
import time

import tpsup.seleniumtools
import tpsup.pstools
import tpsup.envtools
import os

from selenium import webdriver

our_cfg = {
    "module": "tpsup.seleniumtools",

    "usage_example": """
    
    {{prog}} any
    
    """,

}


def code(all_cfg: dict, known: dict, **opt):
    verbose = opt.get("verbose", 0)
    if verbose:
        print(f'from code(), known ={pformat(known)}')
        print(f'from code(), opt = {pformat(opt)}')

    url = "chrome-search://local-ntp/local-ntp.html"

    driver: webdriver.Chrome = all_cfg["resources"]["selenium"]["driver"]

    actions = [
        [f"url={url}"],
        [
            [
                'xpath=/html/body/ntp-app',
                'shadow',
                'css=ntp-realbox',  # within shadow root, only css selector
                'shadow',
                'css=input',
            ],
            [
                f'string=Selenium Python',
                f'key=Enter,1',  # key name is case-insensitive
            ],
            "search",
        ],
    ]

    print(f"test actions = {pformat(actions)}")

    # '-interactive' is passed through **opt
    result = tpsup.seleniumtools.run_actions(driver, actions, **opt)
