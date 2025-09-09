#!/usr/bin/env python
import datetime
import os

import re
import time
from typing import Union

import tpsup.envtools
import json
import tpsup.csvtools
import tpsup.htmltools
import tpsup.appiumtools
import tpsup.locatetools
import tpsup.pstools
from pprint import pformat
# from selenium import webdriver
from appium import webdriver

HOME = tpsup.envtools.get_home_dir()
TPSUP = os.environ['TPSUP']
TPP3 = f'{TPSUP}/python3/scripts'
HTTP_BASE = 'http://localhost:8000'
FILE_BASE = f'file:///{TPP3}'
EXAMPLE_BASE = HTTP_BASE

our_cfg = {
    # this loads specified module's 'tpbatch', which contains
    #    pre_batch(), post_batch(), 'extra_args', ...
    'module': 'tpsup.appiumtools',

    # appiumEnv = AppiumEnv(host_port='localhost:4723', is_emulator=True)

    'usage_example': f'''
    {tpsup.appiumtools.diagarm}

    Note: we won't mention adb_device_name on command line because
        1. appium server will auto find the device from "adb devices"
        2. appium only works when "adb devices" has only one device.
    
    to test with emulator, 
        just add -emu 
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

    - ways to start an emulator
    {{{{prog}}}} start_emulator
    {{{{prog}}}} -emu start_driver    # emulator is started as part of start_driver
    {{{{prog}}}} -emu xpath=//...     # both emulator and driver are started for searching xpath

    - how to find "id" or "xpath" for an element,
    use appium inspector -> start seesion -> right click on the element and inspect
        in the "Selected Element tab", copy thee "id" or "xpath"
       
    {{{{prog}}}} -emu --humanlike '''
                     'start_driver '
                     'home sleep=3 id=com.google.android.apps.nexuslauncher:id/overview_actions_view click '
                     'string=Amazon sendkey=enter sleep=8 '
                     'dump=page={HOME}/dumpdir/page_source.html '
                     'xpath="//*[@content-desc]" '
    # 'context=webview dump_element=stdout '
                     f'''
    
    - test install/uninstall app
      test if-else block
    {{{{prog}}}} -emu start_driver \\
        if=existsapp=org.nativescript.test02ngchallenge \\
            removeapp=org.nativescript.test02ngchallenge \\
        else \\
            installapp="{TPP3}/test02.apk" \\
        end_if \\
        sleep=1

    if app install stuck, 
        adb uninstall org.nativescript.test02ngchallenge
    
    - test webview context
    {{{{prog}}}} -emu start_driver context=webview
    todo: this is not working yet. we may need to launch an webview app first
    
    - find package name
    androidenv set # set android studio (adb) env
    adb shell "pm list packages|grep test02"
    i got "package:org.nativescript.test02ngchallenge"
    this info can also be found in package source code
    
    - find activities' names of the package
    androidenv set
    adb shell "dumpsys package |egrep '^[ ]+[0-9a-z]+[ ]+org.nativescript.test02ngchallenge/'"
        b20ec9c org.nativescript.test02ngchallenge/com.tns.NativeScriptActivity

    - run the package's activity
    {{{{prog}}}} -emu start_driver run=org.nativescript.test02ngchallenge/com.tns.NativeScriptActivity print=currentActivity

    - home, back
    {{{{prog}}}} -emu start_driver print=currentactivity home run=org.nativescript.test02ngchallenge/com.tns.NativeScriptActivity back

    - start an app
    {{{{prog}}}} -emu start_driver ensureapp=org.nativescript.test02ngchallenge \\
        run=org.nativescript.test02ngchallenge/com.tns.NativeScriptActivity

    - click an element, clear text, enter text, click button
      note: I had to use "xpath=//android.widget.EditText[matches(text(), '.*')]" instead of "xpath=//android.widget.EditText"
            will need to find out why
    {{{{prog}}}} -emu start_driver\\
        run=org.nativescript.test02ngchallenge/com.tns.NativeScriptActivity \\
        "xpath=//android.widget.EditText[matches(text(), '.*')]" click clear \\
        string="hello world" \\
        css=android.widget.Button click \\
        "xpath=//*[@id='com.google.android.youtube:id/fullscreen_button']" click \\
        record_screen

    - download a Youtube video - there is no sound 
    {{{{prog}}}} -emu start_driver \\
        home wait=5 sleep=3 \\
        xpath="//android.widget.FrameLayout[@resource-id='com.google.android.apps.nexuslauncher:id/overview_actions_view']" \\
        click sleep=3 \\
        xpath="//android.view.View[@content-desc='Home']" sleep=3 \\
        string="https://youtu.be/3EaKUrU5qjA?si=p0DVT0wFL-s5rWas" \\
        action=search sleep=10 \\
        xpath="//android.widget.ImageView[@content-desc='Enter fullscreen']" \\
        click sleep=5 \\
        record

    the above method is not reliable. the following way is more reliable but more manually.
    open the video youtube in emulator, with disired settings, then
    {{{{prog}}}} -emu start_driver record_screen

    - run with localhost http server to test webview context
        note: 
            http://127.0.1:8000 is the http server on emulator.
            http://10.0.2.2 is the http server on computer (windows or linux)
            webview app examples: chrome, facebook,
    
        start the web server on computer
        cd {TPP3}
        python3 -m http.server 8000

        run chrome on emulator and go to http://10.0.2.2:8000/iframe_over_shadow_test_main.html
        - it took about 10 seconds for WEBVIEW context to be available.
        - once chrome is launched, even if it is in background, WEBVIEW context is available.
        {{{{prog}}}} -emu start_driver \\
            home       sleep=5  print=context  # contexts=['NATIVE_APP'] \\
            run=chrome sleep=10 print=context  # contexts=['NATIVE_APP', 'WEBVIEW_chrome'] \\
            context=webview print=context      # contexts=['NATIVE_APP', 'WEBVIEW_chrome']

        simplied steps to bring up WEBVIEW app (chrome)
        {{{{prog}}}} -emu start_driver \\
            start_http_server \\
            url="http://10.0.2.2:8000" \\
            print=context  # contexts=['NATIVE_APP', 'WEBVIEW_chrome']
        


    
''',


    'show_progress': 1,

    'opt': {
        # 'humanlike': 1, # slow down a bit, more human-like
        # "browserArgs": ["--disable-notifications"],
    },
}


def pre_batch(all_cfg, known, **opt):
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
    explore = opt.get('explore', 0)

    yyyy, mm, dd = datetime.datetime.now().strftime("%Y,%m,%d").split(',')

    steps = known['REMAININGARGS']
    print(f'steps = {pformat(steps)}')

    driverEnv: tpsup.appiumtools.AppiumEnv = all_cfg["resources"]["appium"]['driverEnv']
    result = driverEnv.follow(steps, **opt)
    # if explore mode, enter explore mode at the end of the steps
    if explore:
        print("enter explore mode")
        driverEnv.explore(**opt)

def parse_input_sub(input: Union[str, list], all_cfg: dict, **opt):
    return {'REMAININGARGS': input}
