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
    {{prog}} any
    ''',

    # all keys in keys, suits and aliases (keys and values) will be converted in uppercase
    # this way so that user can use case-insensitive keys on command line
    'keys': {
        'RESOLUTIONCODE': 'Solved (Permanently)',
        'RESOLUTIONNOTES': 'done',
        'CAUSE': 'Process Execution',
        'SUBCAUSE': 'Execution Error',
    },

    'suits': {
        'PROC': {
            'CAUSE': 'Process Execution',
            'SUBCAUSE': 'Execution Error',
        },

        'DATA': {
            'CAUSE': 'Data Error',
            'SUBCAUSE': 'Data Input',
        },
    },

    'aliases': {
        'RC': 'RESOLUTIONCODE',
        'RN': 'RESOLUTIONNOTES',
        'C': 'CAUSE',
        'SC': 'SUBCAUSE',
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
            # in ServiceNow->Incidents, create a filter
            #       Active,         is,                         true
            #
            #       Assigned to,    is (dynamic),               Me
            #
            #       State,          is not one of,              Resolved
            #                                                   Cancelled
            #                                                   Closed
            #
            #    Short description, contains,                  (self-closable)
            # Save the filter as 'my self-closable'
            # run it
            # copy the url for below

            'url==my self-closable url'  # this URL should be replaced by the filter URL
        ],
        ['xpath=//iframe[@name="gsft_main"]', 'frame', 'go to main frame'],
        ['xpath=//div[@id="AC.incident.caller_id"]', 'key=backspace,30',
            'clear caller name', {'post': 'sleep 1'}],
    ]

    print(f'actions = {pformat(actions)}')

    # make sure pass along **opt, which has flogs: -interactive, -show_progress, ...
    tpsup.seleniumtools.run_actions(driver, actions, **opt)

    i = 0
    while True:
        print("")

        i = i + 1
        print(f"---------------- closing {i} --------------------")

        actions2 = [
            [
                '''
                    xpath=//a[contains(@aria-label, "Open record: ")],
                    xpath=//tr[@class="list2_no_records"],
                ''',
                '''code=
                      use strict;
                      use warnings;
                      my $text = $element->get_text();
                      print "seeing text='$text'\n";
                      if ($text eq 'No records to display') {
                         # 'return' will only return from run_actions, cannot return to upper
                         # caller. $we_return is a global var, can be picked up by upper caller.
                         print "we return\n";
                         $we_return = 1;
                      } else {
                         $element->click();
                      }
                ''',
                'list open records',

            ],
            [
                'xpath=//span[contains(text(), "Resolution Information")]',
                'click',
                'click resolution tab'
            ],
            ['tab=3', f"string={known['RESOLUTIONCODE']}", 'resolution code'],
            ['tab=1', f"string={known['RESOLUTIONNOTES']}",
                'resolution notes'],
            ['tab=1', f"string={known['CAUSE']}", 'enter cause'],
            ['tab=1', f"string={known['SUBCAUSE']}", 'enter subcause'],
            ['tab=3', ["click", "sleep=3"], 'click Resolve button'],

            # close popup if found.
            # without closing it, we won't be able to click 'go back' button
            [
                {
                    'locator': 'xpath=//div[@id="ui_notification"]/div[@class="panel-body"]/div/span[@class="icon-cross close"]',
                    'NotFound': 'next',
                },
                'click', 'close popup if found'
            ],

            ['xpath=//button[@onclick="gsftSubtmitBack()"]]', 'click',
             'Go Back'],
            ['code=sleep 2'],
        ]

        result = tpsup.seleniumtools.run_actions(driver, actions2, **opt)
        print(f"result['we_return'] = {result['we_return']}")

        if result['we_return']:
            break

        if opt.get('dryrun', 0) or result['we_return']:
            break

        print("")


def post_batch(all_cfg, known, **opt):
    print(f'running post batch')
    driver = all_cfg['resources']['selenium']['driver']
    driver.quit()
    if tpsup.pstools.prog_running('chromedriver', printOutput=1):
        print(f"seeing leftover chromedriver")
