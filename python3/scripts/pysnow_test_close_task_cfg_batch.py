#!/usr/bin/env python

from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from pprint import pformat
import tpsup.seleniumtools_old
import tpsup.pstools
import tpsup.envtools

our_cfg = {

    'resources': {
        'selenium': {
            'method': tpsup.seleniumtools_old.get_driver,
            'cfg': {}
        },
    },

    'extra_args': [
        {'dest': 'headless', 'default': False,
            'action': 'store_true', 'help': 'run in headless mode'},
    ],

    'usage_example': '''
    - run everything locally and let chromedriver to start the browser and pick the port
    {{prog}} any
    ''',

    # all keys in keys, suits and aliases (keys and values) will be converted in uppercase
    # this way so that user can use case-insensitive keys on command line
    'keys': {
        'ASSIGNTO': 'John Adams',
        'CI': 'My App',
    },

    'suits': {
    },

    'aliases': {
    },

    'keychains': {
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
        # ['url=https://google.com', 'tab=5'],
        [
            # ServiceNow workflow, my automatic way
            #     user (myself) open a request
            #     in the description section, besides normal description, also add a priority, eg, (P3)
            #     after user submitted the request, ServiceNow creates a task from it.
            #     Support member (myself again) open the task.
            #     assign it to myself
            #     assign a priority according the description
            #         eg, if I see "(P3)" in description, I assign priority 3 to the task
            #         default to priority 4
            #     then enter Resolution notes
            #     click Resolve button
            #     ServiceNow will automatically close resolved tasks in 7 days
            #
            # The URL below to a filter under "Service Catalog/Tasks", to list my own self-open tasks
            # filter is
            #     Active is true
            #     State is Open
            #     TaskType is Catalog Task
            #     Created by is <my user id>
            # each of the task can be assigned to Priority 1-4, with 1 the highest
            #
            'url=https://google.com'  # this URL should be replaced by the filter URL
        ],
        ['xpath=//iframe[@name="gsft_main"]', 'frame', 'go to main frame'],
        [
            None,
            'code='+'''
                # this is the initialization code. It is on the same level of other code; therefore
                # no need to make variables global 
                import re
                # in request description, look for (P[1-4]) for priority
                compiled_priority = re.compile('\(P([1-5])\)', re.IGNORECASE)
                priority = 4  # default priority
            ''',
            'compile patterns'
        ],
    ]

    print(f'actions = {pformat(actions)}')

    # make sure pass along **opt, which has flogs: -interactive, -show_progress, ...
    tpsup.seleniumtools_old.run_actions(driver, actions, **opt)

    i = 0
    while True:
        print("")

        i = i+1

        actions2 = [
            [
                'xpath=//a[contains(@aria-label, "Open record: ")],'
                'xpath=//tr[@class="list2_no_records"]',
                [
                    'code=' + '''
                        text = element.text
                        if text = 'No records to display':
                            print("No records found. we return")
                            we_return = 1
                        else:
                            element.click()    
                    ''',
                    'sleep=1',
                ],
                'list open records'
            ],
            [
                'xpath=//span[text()="Description" and contains(@class, "sn-tooltip-basic")]/../../../div[2]/textarea',
                [
                    'code=' + '''
                        priority = 4 # reset priority to default
                        text = element.text
                        print(f'Description text="{text}"')
                        if m:= compiled_priority.search(text):
                            priority, ^_ = m.groups()
                            print(f"found priority='{priority}'")   
                    ''',
                    'sleep=1'
                ],
                'get priority from Description'
            ],
        ]

        result = tpsup.seleniumtools_old.run_actions(driver, actions, **opt)
        print(f"result['we_return'] = {result['we_return']}")

        if result['we_return']:
            break

        print(f"---------------- closing {i} --------------------")

        actions3 = [
            [
                'xpath=//input[@input[@id="sys_display.sc_task.assigned_to"]',
                [
                    'click',
                    'is_attr_empty=value',
                    f"string={known['ASSIGNTO']}"
                ],
                'Assigned to',
            ],
            [
                'click_path=//select[@id="sc_task.priority"]',
                [
                    f"string={result['priority']}",
                    'click'
                ],
                'Set Priority'
            ],
            ['tab=2', 'string=Closed Complete', 'Set State to Closed'],
            ['xpath=//button[@id="sysverb_update"]',
                'click', 'Click Update button'],
        ]

        result = tpsup.seleniumtools_old.run_actions(driver, actions3, **opt)

        if opt.get('dryrun', 0) or result['we_return']:
            break

        print("")

# def post_batch(all_cfg, known, **opt):
#     print(f'running post batch')
#     driver = all_cfg['resources']['selenium']['driver']
#     driver.quit()
#     if tpsup.pstools.prog_running('chrome', printOutput=1):
#         print(f"seeing leftover chrome")
