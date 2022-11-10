#!/usr/bin/env python
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

    "extra_args": [
        {
            "dest": "headless",
            "default": False,
            "action": "store_true",
            "help": "run in headless mode",
        },
    ],
    "usage_example": """
    
    {{prog}} any
    
    """,

}

from pprint import pformat

def code(all_cfg: dict, known: dict, **opt):
    verbose = opt.get("verbose", 0)
    if verbose:
        print(f'from code(), known ={pformat(known)}')
        print(f'from code(), opt = {pformat(opt)}')

    url = "chrome-search://local-ntp/local-ntp.html"

    driver:webdriver.Chrome = all_cfg["resources"]["selenium"]["driver"]

    actions = [
        [f"url={url}"],
        [
            [
                'xpath=/html/body/ntp-app',
                'shadow',
                'css=ntp-realbox', # within shadow root, only css selector
                'shadow',
                'css=input',
            ],
            [
                f'string=Selenium Python',
                f'key=Enter,1', # key name is case-insensitive
            ],
            "search",
        ],
    ]

    print(f"test actions = {pformat(actions)}")

    # '-interactive' is passed through **opt
    result = tpsup.seleniumtools.run_actions(driver, actions, **opt)


def post_batch(all_cfg, known, **opt):
    print(f"running post batch")
    driver:webdriver.Chrome = all_cfg["resources"]["selenium"]["driver"]
    driver.quit()
    if tpsup.pstools.prog_running("chrome", printOutput=1):
        print(f"seeing leftover chrome")
