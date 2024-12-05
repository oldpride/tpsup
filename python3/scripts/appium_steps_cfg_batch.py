#!/usr/bin/env python
import datetime
import os

import time
from typing import Union

import tpsup.envtools
import json
import tpsup.csvtools
import tpsup.htmltools
import tpsup.appiumtools
import tpsup.pstools
from pprint import pformat
# from selenium import webdriver
from appium import webdriver

our_cfg = {
    # this loads specified module's 'tpbatch', which contains
    #    pre_batch(), post_batch(), 'extra_args', ...
    'module': 'tpsup.appiumtools',

    # appiumEnv = AppiumEnv(host_port='localhost:4723', is_emulator=True)

    'usage_example': f'''
    +----------+       +----------+      +-----+    +---------+
    | appium   +------>| appium   +----->+ adb +--->+ phone / | +---->internet
    | python   |       | server   |      |     |    | emulator|
    | webdriver|       |GUI/Nodejs|      |     |    |         |
    +----------+       +----------+      +-----+    +---------+
                       host_port     adb_device_name
    
    host_port is appium sever's host and port.
    adb_device_name is what command "adb devices" shows.
    Note: we won't mention adb_device_name on command line because
        1. appium server will auto find the device from "adb devices"
        2. appium only works when "adb devices" has only one device.
    
    to test with emulator, 
        just add -is_emulator 
        this call will start an emulator

    to test with real device running android,
        on the device, settings->system->developer options->USB debugging, turn on.
        if device is connected with USB cable
            no extra steps  
        if device is connected with Wi-fi (must be on the same wifi network)
            settings->system->developer options-Wireless debugging, turn on
            go into Wireless debugging, 
                under IP address and Port
                    write down the host:port1, 
                    this will be the 'connect' port, not the pairing port.
            if PC and device haven't been paired, do the following
                under Wireless Debugging, click Pair device with pairing code.
                write down the paring code.
                write down the host:port2, which is the pairing port.
                from PC,
                    adb pair host:port2
                    enter pairing code
            from PC command line:
                adb connect "host:port1"
                adb devices
                  "host:port1" will be the device name in the output, and this
                  will be the adb_device_name
                  
    Note: there are many host:port pairs involved
        appium-server host:port
        emulator host:port
        device pairing host:port
        device connect host:port

    {{{{prog}}}} -is_emulator --humanlike '''
                     'key=home id=com.android.quicksearchbox:id/search_widget_text click '
                     'id=com.android.quicksearchbox:id/search_src_text click string=Amazon action=Search '
                     'dump_page=%USERPROFILE%/dumpdir2/page_source.html '
                     'xpath="//*[@content-desc]" '
    # 'context=webview dump_element=stdout '
                     f'''
    
    - test with app - this command installs the app too if not installed yet.
    {{{{prog}}}} -is_emulator -v -np -app "%TPSUP%/python3/scripts/test02.apk" sleep=1
    - if app stuck, 
    adb uninstall org.nativescript.test02ngchallenge
    
    - test webview context
    {{{{prog}}}} -is_emulator context=webview
    todo: this is not working yet. we may need to launch an webview app first
    
    - test with real device, 
    - the following command load the package onto the device
    {{{{prog}}}} -np -v -app "%TPSUP%/python3/scripts/test02.apk" sleep=1
    
    - find package name
    adb shell "pm list packages|grep test02"
    i got "package:org.nativescript.test02ngchallenge"
    this info can also be found in package source code
    
    - find activities' names of the package
    adb shell "dumpsys package |egrep '^[ ]+[0-9a-z]+[ ]+org.nativescript.test02ngchallenge/'"
        b20ec9c org.nativescript.test02ngchallenge/com.tns.NativeScriptActivity

    - run the package's activity
    {{{{prog}}}} -np -v run=org.nativescript.test02ngchallenge/com.tns.NativeScriptActivity

    - the above can be done in one command assuming knowing pkg and activity beforehand
    {{{{prog}}}} -np -v -app "%TPSUP%/python3/scripts/test02.apk" run=org.nativescript.test02ngchallenge/com.tns.NativeScriptActivity

    - block (if/while/not) examples see notes/wechat.txt
    
''',


    'show_progress': 1,

    'opt': {
        # 'humanlike': 1, # slow down a bit, more human-like
        # "browserArgs": ["--disable-notifications"],
    },
}


def pre_batch(all_cfg, known, **opt):
    steps = known['REMAININGARGS']
    print(f'steps = {pformat(steps)}')

    # check first, then run. this saves time to catch errors early.
    print(f'---------- begin checking steps -----------')
    tpsup.appiumtools.follow(None, steps, checkonly=1, **opt)
    print(f'---------- end checking steps -----------')

    # call the default pre_batch() from tpsup.appiumtools
    tpsup.appiumtools.pre_batch(all_cfg, known, **opt)


def code(all_cfg, known, **opt):
    verbose = opt.get('verbose', 0)
    if verbose:
        print(f'from code(), known ={pformat(known)}')
        print(f'from code(), opt = {pformat(opt)}')

    dryrun = opt.get('dryrun', 0)
    run_js = opt.get('js', 0)
    trap = opt.get('trap', 0)

    yyyy, mm, dd = datetime.datetime.now().strftime("%Y,%m,%d").split(',')

    steps = known['REMAININGARGS']
    print(f'steps = {pformat(steps)}')

    driver: webdriver = all_cfg["resources"]["appium"]["driver"]

    result = tpsup.appiumtools.follow(driver, steps, **opt)

    if verbose:
        print(f'result = {pformat(result)}')


def parse_input_sub(input: Union[str, list], all_cfg: dict, **opt):
    return {'REMAININGARGS': input}
