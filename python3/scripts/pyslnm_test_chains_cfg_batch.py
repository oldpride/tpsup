#!/usr/bin/env python
from pprint import pformat
import time

import tpsup.seleniumtools_old
import tpsup.pstools
import tpsup.env
import os

from selenium import webdriver

our_cfg = {
    "module": "tpsup.seleniumtools",

    "usage_example": """
    $ {{prog}}  any
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
        [f"url={url}", "sleep=2", 'go to url'],
        [
            {
                'chains': [
                    # branch in the beginning
                    [
                        'xpath=/html/body[1]/ntp-app[1]', 'shadow',
                        'css=#mostVisited', 'shadow',
                        'css=#removeButton2',  # correct on ewould be 'css=#removeButton'. we purposefully typoed
                    ],
                    [
                        'xpath=/html/body[1]/ntp-app[1]', 'shadow',
                        'css=#mostVisited', 'shadow',
                        'css=#actionMenuButton'
                    ],
                ],
            },
            {
                # first number is the chain number, followed by locator number
                '0.0.0.0.0.0': 'code=print("found remove button")',
                '1.0.0.0.0.0': 'code=print("found action button")',
            },
            "test chains",
        ],
        [
            {
                'chains': [
                    # branch in the end
                    [
                        'xpath=/html/body[1]/ntp-app[1]', 'shadow',
                        'css=#mostVisited', 'shadow',
                        '''
                        css=#removeButton2,
                        css=#actionMenuButton
                        ''',
                    ],
                ]
            },
            {
                '0.0.0.0.0.0': 'code=print("found remove button again")',
                '0.0.0.0.0.1': 'code=print("found action button again")',
            },
            "test chains again",
        ],
    ]

    print(f"test actions = {pformat(actions)}")

    # '-interactive' is passed through **opt
    result = tpsup.seleniumtools_old.run_actions(driver, actions, **opt)

    # interval = 2
    # print(f"sleep {interval} seconds so that you can see")
    # time.sleep(interval)
