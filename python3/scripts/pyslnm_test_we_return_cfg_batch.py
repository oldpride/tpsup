#!/usr/bin/env python
from pprint import pformat
import time

import tpsup.seleniumtools_old
import tpsup.pstools
import tpsup.env
import os

our_cfg = {
    "module": "tpsup.seleniumtools",

    "usage_example": """
    - because we need a load static test page, we run everything locally and let chromedriver 
      to start the browser and pick the port.
      the following is tested working in linux, windows cygwin/gitbash/cmd.exe.
    $ {{prog}} s=henry
    
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
}


def code(all_cfg: dict, known: dict, **opt):
    verbose = opt.get("verbose", 0)
    if verbose:
        print(
            f"""
from code(), known =
{pformat(known)}

from code(), opt =
{pformat(opt)}

"""
        )

    my_env = tpsup.env.Env()
    url = None
    if my_env.isCygwin:
        # when we run from cygwin, env var $TPSUP is /cygdrive/c/...
        # it is passed to windows program python.exe which doesn't
        # what to do with this path. therefore. we need to convert
        # from format like:
        #     /cygdrive/c/Program Files;/cygdrive/c/Users;/cygdrive/d
        # to
        #     c:/Program Files;c:/Users;d:
        cyg_path = os.environ.get("TPSUP", "")
        win_path = my_env.cygpath(cyg_path, "cyg2win")
        url = f"file:///{win_path}/scripts/tpslnm_test_input.html"
    else:
        tpsup_path = os.environ.get("TPSUP", "").replace("\\", "/")
        url = f"file:///{tpsup_path}/scripts/tpslnm_test_input.html"

    driver = all_cfg["resources"]["selenium"]["driver"]

    print(
        f"getattr(tpsup.seleniumtools, 'we_return')={getattr(tpsup.seleniumtools_old, 'we_return')}")
    print(f"tpsup.seleniumtools.we_return={tpsup.seleniumtools_old.we_return}")

    actions = [
        [f"url={url}"],
        [
            """xpath=//input[@id="user id"],
            css=#user\ id,
            xpath=//tr[class="non exist"]
         """,
            [
                "click",
                f'string={known["USERID"]}',
                "code=js_print_debug(driver, element)",
            ],
            "enter user id",
        ],
        [
            "tab=4",
            [
                """code=
                    we_return=1 # we_retun is gloabl var only in tpsup.seleniumtools
                    print("we return")
                """,
                """code=print("shouldn't print this line after we return")""",
            ],
            "set we return",
        ],
        [
            None,
            [
                """code=print("Again, shouldn't print this line after we return")"""
            ],
            "after we return",
        ],
    ]
    print(f"test actions = {pformat(actions)}")

    result = tpsup.seleniumtools_old.run_actions(driver, actions)

    # we can access we_return from result
    print(f"result['we_return'] = {result['we_return']}")
    print(
        f"getattr(tpsup.seleniumtools, 'we_return')={getattr(tpsup.seleniumtools_old, 'we_return')}")
    print(f"tpsup.seleniumtools.we_return={tpsup.seleniumtools_old.we_return}")

    interval = 2
    print(f"sleep {interval} seconds so that you can see")
    time.sleep(interval)
