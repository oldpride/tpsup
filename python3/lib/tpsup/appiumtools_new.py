import base64
import os
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import urlparse
from shutil import which

import lxml.etree
from appium import webdriver

from appium.webdriver.appium_service import AppiumService
from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver import WebElement
from appium.options.android import UiAutomator2Options

# import appium webdriver extensions
import appium.webdriver.extensions.android.nativekey as nativekey
# from appium.webdriver.common.touch_action import TouchAction
# https://stackoverflow.com/questions/75881566/ 
# TouchAction class is being deprecated, and the documentation recommends to use ActionChains

from selenium.webdriver import ActionChains

import tpsup.envtools
import tpsup.filetools

import tpsup.locatetools_new
from tpsup.logbasic import log_FileFuncLine
from tpsup.nettools import is_tcp_open, wait_tcps_open
import tpsup.pstools
import tpsup.seleniumtools
import tpsup.tmptools
from tpsup.human import human_delay
import os.path
from tpsup.logtools import tplog
from tpsup.interactivetools import hit_enter_to_continue
from tpsup.exectools import exec_into_globals, multiline_eval
from tpsup.adbtools import adb_wait_screen

from typing import List, Union
from pprint import pformat


diagarm = '''
                         host_port   adb_device_name  phone/emulator
    +----------+       +----------+      +------+    +---------------+
    | appium   +------>+ appium   +----->+ adb  +--->+ adbd          |
    | python   |       | server   | adb  |server|    |               |
    | webdriver|       | Nodejs   | cmd  |      |    |               +---->internet
    |          |       |          |      |:5037 |    | UIAutomator2. |
    |          |       |          |      +------+    | UIAutomator2. |
    |          |       |          |                  | Bootstrap.jar |
    |          |       |          |                  | runs a TCP    |
    |          |       |          |                  | listening port|
    |          |       | REST     |                  |               |
    |          |       | :4723    |----------------->| :5444 emulator|
    |          |       |          |   HTTP  W3C      |               |
    +----------+       +----------+                  +---------------+    
    
    host_port is appium sever's host and port.
    adb_device_name is what command "adb devices" shows.

    UIAutomator2 opens listening port at 8200..8299. start with and default to 8200.
    to 
'''

# global variables
gv = {}

# driver: webdriver.Remote = None # not webdriver.Chrome!
# # we use this to control both explicit and implicit wait. 
# # more detail about explicit and implicit wait, see other comments in this file.
# wait_seconds = 10 # seconds

# # "last_element" is the last element we concerned.
# # note: this may not be the active element. For example, if the previous step
# # used xpath to find an element, the element is the "last_element", but only
# # if we click on it, it become active.
# # however, if we just want to get attribute or dump the element, we can just
# # use the "last_element".
# last_element = None

# # run these locators before or after each step
# debuggers = {
#     'before': [],
#     'after': [],
# }

# appium starting emulator
#   https://appium.io/docs/en/writing-running-appium/running-tests/
#   https://stackoverflow.com/questions/42604543/launch-emulator-from-appium-python-client
def start_proc(proc: str, **opt):
    if proc != 'emulator' and proc != 'appium':
        raise RuntimeError(
            f"start_process() must be either emulator or appium")

    host_port = opt.get(f'{proc}_host_port', None)
    
    if not host_port:
        if proc == 'emulator':
            host_port = 'localhost:5554'
        else:
            # appium server
            host_port = 'localhost:4723'

    (host, port) = host_port.split(":", 1)
    if is_tcp_open(host, port):
        log_FileFuncLine(f"{proc}_host_port={host_port} is already open")
        return {'status': 'open', 'error': 0, 'host_port': host_port}
    else:
        log_FileFuncLine(f"{proc}_host_port={host_port} is not open")

    if host.lower() != "localhost" and host != "127.0.0.1" and host != "":
        log_FileFuncLine(f"we can only start local {proc}; we cannot start remote {proc}")
        if opt.get('dryrun', 0):
            log_FileFuncLine("this is dryrun, so we continue")
            return {'status': 'cannot start', 'error': 1}
        else:
            raise RuntimeError("cannot proceed")

    log = opt.get('log', None)
    if not log:
        log = os.path.expanduser("~") + f"/{proc}.log"

    # https://developer.android.com/studio/run/emulator-commandline
    # https://stackoverflow.com/questions/42604543/launch-emulator-from-appium-python-client
    if proc == 'emulator':
        # android studio -> virtual device manager -> select emulator -> edit -> name it to below
        # emulator and its name is saved under c/Users/tian/.android/avd dir
        emulator_name = "myemulator"
        cmd = f"{os.environ['ANDROID_HOME']}/emulator/emulator -netdelay none -netspeed full " \
              f"-avd {emulator_name} -port {port}"
        if opt.get('headless', False):
            cmd += " -no-window"
        # else:
        #     cmd = f"appium --address localhost -p {port} --log-no-colors"
        #             # f"--log={self.appium_log}","
        log_FileFuncLine(f"cmd = {cmd}")
        with open(log, "w+") as log_ofh:
            # run cmd and check if it started successfully
            # subprocess.Popen(
            #     cmd, shell=True, stderr=subprocess.STDOUT, stdout=log_ofh)
            p = subprocess.Popen(cmd, shell=True, stderr=subprocess.STDOUT, stdout=log_ofh)
            time.sleep(1) # give it a second to start
            if p.poll() is not None:
                raise RuntimeError(f"failed to start {cmd}, see log={log}")

        return {'status': 'started', 'error': 0, 'host_port': host_port}
    else:
        # appium server args
        #   https://appium.io/docs/en/writing-running-appium/server-args/

        service = AppiumService()

        args = [
            "--address", "127.0.0.1",  # this works
            # "--address", "0.0.0.0",  # this works on command line but in this script. Why?
            "--port", f"{port}",
            "--log-no-colors",
            "--base-path", opt['base_path'],
            "--log", log,
            "--log-level", "debug",
        ]
        # f"--log={self.appium_log}"

        log_FileFuncLine(f"starting cmd = appium {' '.join(args)}")
        service.start(args=args)
        log_FileFuncLine(f"service.is_running={service.is_running}")
        log_FileFuncLine(f"service.is_listening={service.is_listening}")
        # service.stop()
        return {
            'status': 'started',
            'error': 0,
            'service': service,
            'host_port': host_port
        }


def get_setup_info():
    return '''
{diagarm}

to test with emulator, 
    just set is_emulator = True.
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
        '''

class AppiumEnv:
    # will come from locatetools_new
    locate: callable = None
    follow: callable = None
    explore: callable = None

    driver: webdriver.Remote = None

    # we use this to control both explicit and implicit wait. 
    # more detail about explicit and implicit wait, see other comments in this file.
    wait_seconds:int = 10 # seconds

    # "last_element" is the last element we concerned.
    # note: this may not be the active element. For example, if the previous step
    # used xpath to find an element, the element is the "last_element", but only
    # if we click on it, it become active.
    # however, if we just want to get attribute or dump the element, we can just
    # use the "last_element".
    last_element:WebElement = None

    printables = ['contexts', 'currentActivity', 'html', 
                  'tag', 'text', 'title', 'timeouts', 
                  'url', 'xpath']

    need_wait: List[dict] = []

    def __init__(self, 
                 host_port: str, 
                 base_path: str = '/wd/hub',
                 clean = False, # whether to remove server and driver persistent data and logs
                 cleanQuit = False, # whether to remove server and driver persistent data and logs and quit
                 is_emulator = False, # whether to connect to an emulator             
                 **opt):
        # host_port is appium server's host and port,
        #   not to be confused with emulator's host and port.
        #   if host_port is not open and host is localhost, this call will start
        #   the appium server at the port.
        # note: we don't need to specify deviceName as shown in 'adb devices' because the
        #   appium server will automatically find the device and
        #   appium only support one device.

        self.host_port = host_port

        '''
        base_path is called "remove path" in appium inspector.
            it is part of the appium server's url, eg, http://localhost:4723/wd/hub
            if appium (server) is started without --base-path, the url will be http://localhost:4723/
            if appium is started with --base-path /wd/hub, the url will be http://localhost:4723/wd/hub
        '''
        self.base_path = base_path
        
        self.verbose = opt.get("verbose", 0)
        # self.env = tpsup.envtools.Env()
        # self.env.adapt()
        # home_dir = os.path.normpath(
        #     self.env.home_dir)  # get_native_path() is for cygwin
        self.home_dir = tpsup.envtools.get_home_dir()
        self.downloads_dir = tpsup.envtools.get_downloads_dir()

        self.log_base = opt.get('log_base', f"{self.home_dir}/appium")

        # self.page_load_timeout = opt.get('page_load_timeout', 30)
        self.dryrun = opt.get("dryrun", False)

        self.emulator_log = os.path.join(self.log_base, "emulator.log")
        self.appium_log = os.path.join(self.log_base, "appium.log")

        if clean or cleanQuit:
            self.clean()
            if cleanQuit:
                exit(0)

        self.is_emulator = is_emulator

        if self.is_emulator:
            log_FileFuncLine(f"emulator_log={self.emulator_log}")
            
        self.appium_exe = which('appium')
        if self.appium_exe:
            log_FileFuncLine(f"appium is {self.appium_exe}")
        else:
            raise RuntimeError(f"appium is not in PATH={os.environ['PATH']}\nnormally C:/tools/nodejs/appium")
        
        log_FileFuncLine(f"appium_log={self.appium_log}")

        self.driver: webdriver.Remote = None

        static_setup = tpsup.seleniumtools.get_static_setup(**opt)
        chromedriver_path = static_setup.get('chromedriver', None)
        if not chromedriver_path:
            raise RuntimeError(f"chromedriver is not set in static_setup={static_setup}")

        # looks appium 2.0 deprecated desired_capabilities, use capabilities instead.
        # https://appium.io/docs/en/latest/quickstart/test-py/
        self.capabilities = dict(
            platformName='Android',
            automationName='UiAutomator2',
            # deviceName='Android',
            # appPackage='com.android.settings',
            # appActivity='.Settings',
            # language='en',
            # locale='US',

            # chromedriver
            #   1. this is called only when driver.switch_to.context("webview...")
            #      it may only work when desired_capacity has "app" set
            #      https://github.com/appium/appium-inspector/issues/465
            #      otherwise, error: unrecognized chrome option: androidDeviceSerial
            #   2. chromedriver's version must match chrome version on the device.
            chromedriverExecutable=chromedriver_path,
        )

        # these two can be replaced with run=app/activity
        if app := opt.get("app", None):
            self.capabilities['appPackage'] = app  # this actually installs the app
        if act := opt.get("act", None):
            self.capabilities['appActivity'] = act

        self.opt = opt
        
        locateEnv = tpsup.locatetools_new.LocateEnv(
            locate_cmd_arg=self.locate_cmd_arg,
            locate_usage_by_cmd=self.locate_usage_by_cmd,
            **opt)
        self.locate = locateEnv.locate
        self.follow = locateEnv.follow
        self.explore = locateEnv.explore

        log_FileFuncLine(f"capabilities = {pformat(self.capabilities)}")
        # https://www.youtube.com/watch?v=h8vvUcLo0d0

        log_FileFuncLine(f"driverEnv is created. driver will be created when needed by calling driverEnv.get_driver()")

        # we only set up driverEnv, not initializing driver.
        # we initialize driver when get_driver() is called on demand.


    def start_emulator(self):
        print()
        print(f"starting emulator if not already started")
        response = start_proc('emulator', log=self.emulator_log, **self.opt)
        status = response.get('status', None)
        if status == "open":
            log_FileFuncLine(f"emulator is already started at {response.get('host_port')}, log={self.emulator_log}")
        elif status == "started":
            log_FileFuncLine(f"emulator is started but need to wait for {response.get('host_port')} to be ready")
            self.need_wait.append({
                'host_port': response.get('host_port'),
                'app': 'emulator'
            })
        else:
            raise RuntimeError(f"emulator is being started. log={self.emulator_log}")

        return response

    def start_driver(self, **opt) -> webdriver.Remote:
        if self.is_emulator:
            self.start_emulator()

        print()
        print(f"starting appium server if not already started")
        response = start_proc('appium', log=self.appium_log, base_path=self.base_path, **self.opt)
        status = response.get('status', None)
        if status == "open":
            log_FileFuncLine(f"appium server is already started at {response.get('host_port')}, log={self.appium_log}")
        elif status == "started":
            self.need_wait.append({
                'host_port': response.get('host_port'),
                'app': 'appium'
            })
    
        log_FileFuncLine(f"appium response = {pformat(response)}")
        self.service: AppiumService = response.get('service', None)
        
        self.wait_open(60)
            
        print(f"starting webdriver session (appium.webdriver). this is not a separate process.")
        # https://appium.io/docs/en/latest/quickstart/test-py/
        # we use /wd/hub here because we set --base-path /wd/hub in appium server (see above)
        appium_server_url = f"http://{self.host_port}{self.base_path}"
        print()
        print(f"connecting to appium_server_url={appium_server_url}")
        if not self.driver:
            connected = False
            try:
                '''
                appium.webdriver is a subclass of selenium.webdriver.Remote.
                    see venv/Windows/win10-python3.12/Lib/site-packages/appium/webdriver/webdriver.py
                selenium.webdriver.Remote class is actually selenium.webdriver.remote.webdriver.WebDriver class
                    see venv/Windows/win10-python3.12/Lib/site-packages/selenium/webdriver/__init__.py
                        from .remote.webdriver import WebDriver as Remote
                '''

                self.driver = webdriver.Remote(
                    appium_server_url, 
                    options=UiAutomator2Options().load_capabilities(self.capabilities))
                connected = True
                # appium implicit wait is default 0. there is no get_implicitly_wait() method
                # self.driver.implicitly_wait(60)
            except Exception as e:
                print(f"Exception: {e}")
                print(
                    "both appium and device/emulator are running, but webdriver failed to connect")
                print("likely device/emulator is still booting up.")

            if not connected:
                sleep_time = 40
                print(f"sleep {sleep_time} seconds and try again")
                time.sleep(sleep_time)
                self.driver = webdriver.Remote(
                    appium_server_url, 
                    options=UiAutomator2Options().load_capabilities(self.capabilities))
                
            log_FileFuncLine(f"started appium.webdriver.Remote and connected to {appium_server_url}\n")

            self.driver.driverEnv = self  # monkey patching for convenience   
        return self.driver

    def wait_open(self, max_wait: int)-> bool:
        if not self.need_wait:
            print("no need to wait")
            return True

        print(f"wait up to {max_wait} seconds for:")
        for item in self.need_wait:
            print(f"    {item['app']} at {item['host_port']} to be open")
        
        # get host_port list to wait
        host_port_list = []
        for item in self.need_wait:
            host_port_list.append(item['host_port'])

        return wait_tcps_open(host_port_list, timeout=max_wait)

    def close_env(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
        if self.service:
            self.service.stop()
            self.service = None

    def is_healthy(self):
        print(f"service.is_running={self.service.is_running}")
        print(f"service.is_listening={self.service.is_listening}")
        return (self.driver.session_id and self.service.is_listening and self.service.is_running)
    
    # def get_home_dir(self) -> str:
    #     return self.home_dir
    
    # def get_downloads_dir(self) -> str:
    #     return self.downloads_dir

    def clean(self):
        # remove driver log and chromedir
        for f in [self.appium_log, self.emulator_log]:
            if self.debug:
                log_FileFuncLine(f"removing {f}")
            try:
                shutil.rmtree(f)
            except FileNotFoundError:
                if self.debug:
                    log_FileFuncLine(f"{f} not found")
            except NotADirectoryError:
                if self.debug:
                    os.remove(f)

    locate_usage_by_cmd = {
        'action': {
            'usage': '''
            examples:
                action    # default to search
                action=search
                ''',
        },
        'back': {
            'no_arg': True,
            'usage': 'click back button',
        },
        'check_procs': {
            'no_arg': True,
            'usage': '''
            check if process is running, eg, adb, emulator (qemu), appium (node), chromedriver
            ''',
        },
        'clear': {
            'no_arg': True,
            'usage': '''
            clear the content of last_element
            ''',
        },
        'click': {
            'no_arg': True,
            'siblings': ['doubleclick'], # siblings cmd share the same usage
            'usage': '''
            click the last_element
            ''',
        },
        'code': {
            'need_arg': True,
            'has_dryrun': True,
            'siblings': ['python', 'exp', 'js'],
            'usage': '''
            code=python code
            python=python code
            exp=python expression which returns True/False or equivalent (eg, 1 vs 0, "abc" vs "").
            js=javascript code
            js=file=filename.js
            js=file2element=filename.js

            examples:
                code=print("hello world")
                python=print("hello world")
                exp=i==1
                js=console.log("hello world")
                js=file=filename.js
                code=2print="1+1"
                code=file=filename.py
                js=file2element=filename.js
                js=2element="return document.querySelector('body')"
            ''',
        },
        'context': {
            'need_arg': True,
            'has_dryrun': True,
            'usage': '''
            switch context.
            examples:
                context=native
                context=webview

            to print current context
                print=context
            ''',
        },
        'dump': {
            'need_arg': True,
            'usage': '''
            dump=element|page=path
            element|page is optional, default is element
            path is optional, default path is ~/dumpdir
            examples:
                dump
                dump=element
                dump=page
                dump=element=./mydumpdir
                dump=page=./mydumpdir
            ''',
        },
        'ensureapp': {
            'need_arg': True,
            'siblings': ["existsapp", "installapp", "reinstallapp", "removeapp"],
            'usage': '''
            ensure app is installed; if not, install it
            example
                ensureapp=com.example.myapp
                existsapp=com.example.myapp
                installapp=com.example.myapp
            ''',
        },
        'home': {
            'no_arg': True,
            'usage': 'click home button',
        },
        'kill_procs': {
            'no_arg': True,
            'usage': '''
            kill process, eg, adb, emulator (qemu), appium (node), chromedriver
            ''',
        },
        'print': {
            'need_arg': True,
            'has_dryrun': True,
            'usage': '''
            print=key1,key2,...
            key can be one of:
                contexts
                currentActivity
                html
                tag
                text
                title
                timeouts
                url
                xpath (last_element's xpath)
            ''',
        },
        'record': {
            'usage': '''
            record=video_file
            start recording the screen to video_file
            if video_file is not specified, it will be saved in ~/downloads/record_screen.mp4
            example:
                record
                record=c:/users/me/downloads/myrecord.mp4
            ''',
        },
        'refresh': {
            'no_arg': True,
            'usage': 'refresh the current page',
        },
        'run': {
            'has_dryrun': True,
            'usage': '''
            run=app/activity
            example:
                run        # default to chrome
                run=chrome
                run=com.android.chrome/com.google.android.apps.chrome.Main
            ''',
        },
        'screenshot': {

            'usage': '''
            take a screenshot
            example:
            screenshot
            screenshot=downloads_dir
            if downloads_dir is not specified, it will be saved in ~/downloads
            ''',
        },
        'sendkey': {
            'need_arg': True,
            'has_dryrun': True,
            'usage': '''
            send key to device. key is from androidkey.AndroidKey. 
            eg, ENTER,
            ''',
            },
        'sleep': {
            'need_arg': True,
            'usage': 'sleep=3',
        },
        'start_driver': {
            'no_arg': True,
            'usage': 'start the driver if not already started',
        },
        'start_emulator': {
            'no_arg': True,
            'usage': 'start the emulator if not already started',
        },
        'string': {
            'need_arg': True,
            'usage': '''
            string=value
            rawstring=value
            value can be multi-line.

            for non-rawstring, tab will be replaced with 4 spaces.
            ''',
        },
        'swipe': {
            'need_arg': True,
            'usage': '''
            swipe=direction,size
            direction can be one of: left, right, up, down
            size is optional, can be one of: small, medium, large
            default size is medium
            examples:
                swipe=up    # default size is medium
                swipe=down,small
                swipe=small,down
                swipe=left,large
                swipe=right,large
            ''',
        },
        'url': {
            'need_arg': True,
            'usage': 'url=http://example.com',
        },
        'wait': {
            'need_arg': True,
            'usage': '''wait=impl=10
            wait=expl=10
            wait=page=10
            wait=all=10
            ''',
        },
        'wait_open': {
            'need_arg': True,
            'usage': 'wait_open=30  # wait up to 30 seconds for needed host:port to be open',
        },
        'xpath': {
            'need_arg': True,
            'has_dryrun': True,
            'siblings': ['css', 'id'],
            'usage': '''
            xpath=//tag[@attr='value']
            css=.class or tag.class or tag#id
            id=id_value
            ''',
        },
    }

    def locate_cmd_arg(self, cmd: str, arg: str, **opt) -> dict:
        '''
        locate_cmd_arg() is not called directly in this file.
        it is a component of locate() in locatetools_new.py
        '''
        dryrun = opt.get("dryrun", 0)
        # interactive = opt.get("interactive", 0)
        debug = opt.get("debug", 0)
        verbose = opt.get("verbose", debug)
        isExpression = opt.get("isExpression", 0) # for condtion test, we set isExpression=1, so that we get True/False.

        # global driver
        # global last_element
        # global wait_seconds
        # global debuggers

        ret = tpsup.locatetools_new.ret0.copy()
        ret['Success'] = True # set default to True

        '''
        examples can be found in github test folder
        https://github.com/appium/python-client/tree/master/test
        '''

        if cmd == 'action':
            if not arg:
                arg = 'Search'
            # driverEnv = get_driverEnv(**opt)
            # if driverEnv.is_emulator:
            if self.is_emulator:
                # this is for emulator, there is no virtual keyboard,
                # we can not click the search button on the emulator,
                # so we type Enter key
                self.locate(f"sendkey=enter", **opt)
            else:
                # this is for real device, there is a virtual keyboard,
                # we click the search button on the virtual keyboard
                self.driver.execute_script(
                    'mobile: performEditorAction', {'action': arg})
        elif cmd == 'back':
            self.driver.back()
        elif cmd == 'check_procs':
            tpsup.pstools.check_procs(procs)
        elif cmd == 'clear':
            if not self.last_element:
                raise RuntimeError("last_element is None")
            self.last_element.clear()
        elif cmd == 'click':
            self.last_element.click()
        elif cmd in ['code', 'python', 'exp', 'js']:
            lang = cmd
            '''
            'code' and 'python' are the same - python code to be executed.
            'exp' is python code which returns True/False or equivalent (eg, 1 vs 0, "abc" vs "").
            examples
                code=print("hello world")
                python=print("hello world")
                exp=i==1
                js=console.log("hello world")
                js=file=filename.js
                code=2print="1+1"
                code=file=filename.py
                js=file2element=filename.js
                js=2element="return document.querySelector('body')"
            '''

            m = re.match(r"(file)?(.*?)=(.+)", arg, re.MULTILINE | re.DOTALL)
            if not m:
                raise RuntimeError(f"invalid {lang} argument {arg}")
            file, target, code = m.groups()

            if file:
                # code is a file name, read the file content
                filename = code
                if filename.startswith('~'):
                    filename = os.path.expanduser(filename)
                
                elif not os.path.isabs(filename):
                    # relative path, relative to current working dir
                    filename = os.path.abspath(filename)

                if not os.path.exists(filename):
                    raise RuntimeError(f"{lang} file {filename} doesn't exist")

                with open(filename) as f:
                    code = f.read()
                print(f"locate: read {lang} from file {filename}:\n{code}")
            else:
                print(f"locate: run {lang}: {code}")

            # parse 'target'
            if target:
                if m := re.match(r"2(print|pformat|element)+$", target):
                    target = m.group(1)
                else:
                    raise RuntimeError(f"unsupported target={target}")
            
            if dryrun:
                return ret
            
            if lang in ['code', 'python', 'exp']:
                if isExpression or lang == 'exp' or (target and 'element' in target):
                    # we are testing condition, we want to know True/False
                    # cc = compile(code, '<string>', 'single')
                    code_run_fine = False
                    try:
                        # ret['Success'] = -eval(cc)
                        result = multiline_eval(code, globals(), locals())
                        code_run_fine = True
                        print(f"lang={lang} returns {result}")
                    except Exception as e:
                        print(f"eval failed with exception={e}")
                        ret['Success'] = False

                    if code_run_fine:
                        if target:
                            if 'element' in target:
                                element = self.driver.switch_to.active_element
                                element.send_keys(result)
                                self.last_element = element
                            elif 'print' in target:
                                print(result)
                            elif 'pformat' in target:
                                print(pformat(result))
                            else:
                                raise RuntimeError(f"lang={lang} doesn't support target={target}.")
                            # note 'result' could be a empty string, which is False in python.
                            # therefore we don't use 'result' to set ret['Success']
                        else:
                            ret['Success'] = result
                else:
                    exec_into_globals(code, globals(), locals())
            elif lang == 'js':
                gv['jsr'] = self.driver.execute_script(code)
                if debug:
                    print(f"locate: jsr={pformat(gv['jsr'])}") # this is too verbose
                if 'element' in target:
                    '''
                    jsr can be an element or a dict with possible keys: 
                    element, shadowHost, iframeElement
                    '''
                    if type(gv['jsr']) == dict:
                        '''
                        keys in the dict
                            'element' and 'iframeElement' can not be in the same dict.
                            'element' and 'shadowHost' can be in the same dict.
                            'shadowHosts' and 'iframeElement' can be in the same dict: shaodowHosts first, then iframe.
                                this is because every 'iframe' will end a piece of js. see locator_chain_to_js_list().
                                therefore, we parse shadowHosts first, to make sure shadowHosts in the front of iframe
                                in domstack.
                        '''

                        # print(f"locate: jsr={pformat(jsr)}") # this is too verbose
                        print("locate: jsr=", end="")
                        for key in gv['jsr']:
                            print(f" {key}={type(gv['jsr'][key])}")
                        if "element" in gv['jsr']:
                            element = gv['jsr']['element']
                            self.last_element = element

                    elif isinstance(gv['jsr'], WebElement):
                        # jsr is an instance of element
                        print(f'locate: jsr={type(gv['jsr'])}')
                        self.last_element = gv['jsr']
                    else:
                        print(f"locate: jsr is not an element nor a dict, but {type(gv['jsr'])}")
                        self.last_element = self.driver.switch_to.active_element
                else:
                    print(f"locate: jsr={pformat(gv['jsr'])}") # this is too verbose
                    self.last_element = self.driver.switch_to.active_element

                if 'print' in target:
                    print(gv['jsr'])

                # https://stackoverflow.com/questions/37791547
                # https://stackoverflow.com/questions/23408668
                # last_iframe = driver.execute_script("return window.frameElement")
                # # pause to confirm
                # print(f"last_iframe={last_iframe}")
   
        elif cmd == 'context':
            if arg not in ['native', 'webview']:
                raise RuntimeError(f"unsupported context={arg}, must be native or webview")

            if dryrun:
                return ret

            contexts = self.driver.contexts
            context = None
            for c in contexts:
                if arg == 'native':
                    if m := re.match(r'native', c, re.IGNORECASE):
                        context = c
                        break
                else:
                    if m := re.match(r'webview', c, re.IGNORECASE):
                        context = c
                        break
            if context:
                print(f"found context={context} among {pformat(contexts)}")
            else:
                raise RuntimeError(
                    f'no matching context among {pformat(contexts)}')
            # when switch to webview context, appium needs a chromedriver
            # selenium.common.exceptions.WebDriverException: Message: An unknown
            # server-side error occurred while processing the command.
            # Original error: No Chromedriver found that can automate Chrome
            # '83.0.4103'. ...
            self.driver.switch_to.context(context)
        elif cmd == 'doubleclick':
            doubleclick(self.driver, element, **opt)
        elif cmd == 'dump':
            '''
            dump=scope=path
            default scope is 'element'
            scope can be 'page' or 'element'

            path is the directory to save the dump.
            default path is ~/dumpdir
            '''
            if not arg:
                scope = 'element'
                path = f"{self.home_dir}/dumpdir"
            else:
                m = re.match(r"(page|element)?(?:=(.+))?", arg)
                if not m:
                    raise RuntimeError(f"invalid dump argument {arg}")
                
                scope, path, *_ = m.groups()
                if not scope:
                    scope = 'element'

                if not path:
                    path = f"{self.home_dir}/dumpdir"
        
            dump(self.driver, self.last_element, scope, path, verbose=verbose)

        elif cmd in ["ensureapp", "existsapp", "installapp", "reinstallapp", "removeapp"]:
            app = arg
            if classmethod == 'ensureapp':
                if not self.driver.is_app_installed(app):
                    self.driver.install_app(app)
                else:
                    print(f"app {app} is already installed")
            elif cmd == 'existsapp':
                ret['Success'] = self.driver.is_app_installed(app)
            elif cmd == 'installapp':
                self.driver.install_app(app)
            elif cmd == 'reinstallapp':
                self.driver.remove_app(app)
                self.driver.install_app(app)
            else:
                self.driver.remove_app(app)
        elif cmd == 'home':
            self.driver.press_keycode(nativekey.AndroidKey.HOME)
        elif cmd == 'kill_procs':
            tpsup.pstools.kill_procs(procs)
        elif cmd == 'print':
            keys = arg.split(",")
            '''
            print=contexts,currentActivity,html,tag,text,title,timeouts,url,xpath
            '''
            # check key is printable
            for key in keys:
                if key not in self.printables:
                    raise RuntimeError(f"unsupported print key={key}")

            print(f"locate: get property {keys}")

            if dryrun:
                return ret
                      
            for key in keys:
                if key == 'contexts':
                    print(f'contexts={self.driver.contexts}')
                elif key == 'currentactivity':
                    print(f'current_activity={self.driver.current_activity}')
                elif key== 'html':
                    if self.last_element:
                        html = self.last_element.get_attribute('outerHTML')
                        print(f'element_html=element.outerHTML={html}')
                elif key == 'tag':
                    # get element type
                    if self.last_element:
                        tag = self.last_element.tag_name
                        print(f'element_tag_name=element.tag_name={tag}')
                elif key == 'text':
                    if self.last_element:
                        text = self.last_element.text
                        print(f'element.text={text}')
                elif key.lower() == 'title':
                    title = self.driver.title
                    print(f'driver.title={title}')
                elif key.lower() == 'timeouts' or key == 'waits':
                    # https://www.selenium.dev/selenium/docs/api/py/webdriver_chrome/selenium.webdriver.chrome.webdriver.html
                    # https://www.selenium.dev/selenium/docs/api/java/org/openqa/selenium/WebDriver.Timeouts.html
                    print(f'    explicit_wait={self.wait_seconds}')    # we will run WebDriverWait(driver, wait_seconds)
                    print(f'    implicit_wait={self.driver.timeouts.implicit_wait}') # when we call find_element()
                    print(f'    page_load_timeout={self.driver.timeouts.page_load}') # driver.get()
                    print(f'    script_timeout={self.driver.timeouts.script}') # driver.execute_script()
                elif key == 'url':
                    '''
                    https://developer.mozilla.org/en-US/docs/Web/URI/Schemes/javascript
                    javascript: URLs can be used anywhere a URL is a navigation target. 
                    This includes, but is not limited to:
                        The href attribute of an <a> or <area> element.
                        The action attribute of a <form> element.
                        The src attribute of an <iframe> element.
                        The window.location JavaScript property.
                        The browser address bar itself.

                    url has mutliple meanings:
                        the url of the current page
                        the url that you go next if you click a link, eg, <a href="url">
                    more accurately, we care about the following urls, from big to small:
                        url = driver.current_url # this driver's url, the top level url of the current page.
                        url = driver.execute_script("return document.referrer") # this is the url of the parent iframe
                        url = driver.execute_script("return window.location.href") # this is my (current) iframe url
                        url = element.get_attribute('src') # if element is iframe, this is child (future) iframe's url
                    '''
                    element_url = None
                    if self.last_element:
                        # the following are the same
                        # element_url = driver.execute_script("return arguments[0].src", last_element)
                        element_url = self.last_element.get_attribute('src')

                        print(f'    element_url=element.get_attribute("src")={element_url}')
                    else:
                        print(f'    element_url is not available because last_element is None')

                    # https://stackoverflow.com/questions/938180
                    iframe_url = self.driver.execute_script("return window.location.href")
                    print(f'    current_iframe_url=window.location.href={iframe_url}')
                    '''
                    1. the following returns the same as above
                        iframe_current = driver.execute_script("return window.location.toString()")
                        print(f'    iframe_current=window.location.toString()={iframe_current}')
                    2. all iframe defined by srcdoc will return "about:srcdoc", eg
                        <iframe srcdoc="<p>hello</p>"></iframe>
                    3. people normally use iframe url to id an iframe, but it is not reliable for
                    srcdoc iframe.
                    '''
                    driver_url = self.driver.current_url
                    print(f'    driver_url=driver.current_url={driver_url}')

                    # https://stackoverflow.com/questions/938180
                    parent_url = self.driver.execute_script("return document.referrer")
                    print(f'    parent_iframe_url=document.referrer={parent_url}')
                elif key == 'xpath':
                    print("xpath is not implemented yet")
                #     if last_element:
                #         xpath = js_get(last_element, 'xpath', **opt)
                #         print(f'element_xpath={xpath}')
                #     else:
                #         print(f'element_xpath is not available because last_element is None')
        elif cmd == 'record':
            '''
            record to a file
            record=filename
            examples:
                record      # default to ~/downloads/record_screen.mp4
                record=C:/Users/me/downloads/record_screen.mp4
            '''
            if not arg:
                # downloads_dir = get_driverEnv().get_downloads_dir()
                downloads_dir = self.downloads_dir
                video_file = os.path.join(downloads_dir, 'record_screen.mp4')
            else:
                video_file = arg

            # make dir if not exist
            os.makedirs(os.path.dirname(video_file), exist_ok=True)

            self.driver.start_recording_screen()

            # we use adb to check screen stillness, to avoid
            # screenshots interfere with screen recording
            adb_wait_screen(until='still')

            video_base64 = self.driver.stop_recording_screen()

            with open(video_file, "wb") as f:
                f.write(base64.b64decode(video_base64))

            print(f"recorded video file is at {video_file}")        
        elif cmd == 'refresh':
            self.driver.refresh()
        # elif m := re.match(r"run=(chrome)$", locator, re.IGNORECASE):
        elif cmd == 'run':
            '''
            run=package_name/activity_name
            run=chrome  # shortcut for run=com.android.chrome/com.google.android.apps.chrome.Main
            run=com.android.chrome/com.google.android.apps.chrome.Main
            '''
            if not arg or arg == 'chrome':
                arg = f"run=com.android.chrome/com.google.android.apps.chrome.Main"
            
            m = re.match(r"(.+?)/(.+)", arg)
            if not m:
                raise ValueError(f"Invalid run argument: {arg}")

            pkg, activity= m.groups()
            
            if dryrun:
                return ret

            self.driver.execute_script(
                'mobile: startActivity',
                {
                    'component': f'{pkg}/{activity}',
                },
            )
        elif cmd == 'screenshot':
            if arg:
                downloads_dir = arg
            else:
                downloads_dir = self.downloads_dir
            filename = f"screenshot.png"
            path = os.path.join(downloads_dir, f"{filename}")
        
            # make dir if not exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.driver.get_screenshot_as_file(path)
        elif cmd == 'sendkey':
            value = arg.upper()
            # https://stackoverflow.com/questions/74188556
            androidkey = nativekey.AndroidKey

            keycode = androidkey.__dict__.get(value, None)
            if not keycode:
                raise RuntimeError(f"key={value} is not supported")
            
            if dryrun:
                return ret
            
            if debug:
                print(f"key={value}, keycode={keycode}")

            # selenium's send_keys is element.send_keys(), using the element as the target.
            # appium's send_keys is driver.press_keycode(), using the driver as the target.
            self.driver.press_keycode(keycode)
        elif cmd == "sleep":
            time.sleep(int(arg))
        elif cmd == 'start_driver': 
            self.driver = self.start_driver(**opt)
        elif cmd == 'start_emulator':
            self.start_emulator()
        elif cmd == 'string' or cmd == 'rawstring':
            if cmd != 'rawstring':
                # replace tab with 4 spaces, because tab will move cursor to the next element.nUX
                arg = arg.replace("\t", "    ")
            result = self.locate(f"code=2element='''{arg}'''", **opt)
            ret.update(result)
        elif cmd == 'swipe':
            swipe(self.driver, arg, **opt)
        elif cmd == "url":
            url = arg
            self.driver.get(url)
        elif cmd == 'wait':
            '''
            wait=impl=10
            wait=expl=10
            wait=page=10
            wait=all=10
            '''
            m = re.match(r"(impl|expl|page|all)*=(\d+)", arg, re.IGNORECASE)
            if not m:
                raise RuntimeError(f"wait=impl|expl|page|all=seconds, got {arg}")
            wait_type, value, *_ = m.groups()
            if not wait_type:
                wait_type = 'all'
            print(f"locate: set {wait_type} wait type to {value} seconds")
            if dryrun:
                return ret

            if wait_type == 'all' or wait_type == 'expl':
                # explicit wait is set when we call WebDriverWait(driver, wait_seconds).
                # explicit wait is done per call (WebDriverWait()).
                # As we are not calling WebDriverWait() here, we only set the global variable,
                # so that it can be used when we call WebDriverWait() in the future.
                self.wait_seconds = int(value)

            if wait_type == 'all' or wait_type == 'impl':
                # driver.implicitly_wait() only set the implicit wait for the driver, 
                # affect all find_element() calls right away.
                # implicit wait is done once per session (driver), not per call.
                # selenium's default implicit wait is 0, meaning no wait.
                self.driver.implicitly_wait(self.wait_seconds)

            # scrpt timeout is not supported in appium
            # if wait_type == 'all' or wait_type == 'script':
            #     # set script timeout
            #     driver.set_script_timeout(int(value))

            if wait_type == 'all' or wait_type == 'page':
                # set page load timeout
                '''
                this is for chromedriver; other driver use implicitly_wait()
                The default value for implicitly_waits is 0, which means
                (and always has meant) "fail findElement immediately if
                the element can't be found."
                You shouldn't be receiving a TimeoutException directly
                from findElement.
                You'll likely only be receiving that when using a
                so-called "explicit wait", using the WebDriverWait construct.
                the code is at
                lib/webdriver line 1353:
                webdriver.Command(webdriver.CommandName.IMPLICITLY_WAIT).
                    setParameter('ms', ms < 0 ? 0 : ms)

                For slow app like Service Now, we need set 30 or more. "
                "Even after page is loaded, it took more time for page to render fully; "
                "therefore, we need to add extra sleep time after page is loaded. "
                "other wait (implicitly wait and explicit wait) is set in 'wait=int' keyvaule",
                '''
                # https://appium.readthedocs.io/en/stable/en/commands/session/timeouts/timeouts/
                # but this only works in webview context, https://github.com/appium/appium/issues/11609
                # todo, turn on below in webview
                # driver.set_page_load_timeout(int(value)*1000)
                pass
        elif cmd == "wait_open":
            '''
            wait for all needed app open
            examples:
                wait_open=60  # wait up to 60 seconds for all needed app open
            '''
            ret['Success'] = self.wait_open(int(arg))
        elif cmd in ["xpath", "css", "id"]:
            tag = cmd
            value = arg
            # AppiumBy.ID is the "resource-id" in uiautomator.
            # we can use dump_page to get the resource-id.
            # example:
            #    <android.widget.TextView index="1" package="com.android.quicksearchbox"
            #      class="android.widget.TextView" text=""
            #      resource-id="com.android.quicksearchbox:id/search_widget_text"
            #      checkable="false" checked="false" clickable="true" enabled="true"
            #      focusable="true" focused="false" long-clickable="false"
            #      password="false" scrollable="false" selected="false"
            #      bounds="[143,130][664,217]" displayed="true"
            #    />
            # resource-id = package_name + element_id
            # here
            #    package_name = com.android.quicksearchbox
            #    element_id = search_widget_tex
            if dryrun:
                if tag == 'xpath':
                    print(f"validate xpath={value}")
                    lxml.etree.XPath(value)
                return ret
            else:
                if tag == 'id':
                    element = self.driver.find_element(AppiumBy.ID, value)
                elif tag == 'xpath':
                    element = self.driver.find_element(AppiumBy.XPATH, value)
                elif tag == 'css':
                    element = self.driver.find_element(AppiumBy.CSS_SELECTOR, value)

                print(f"found element={element}")
                self.last_element = element
        # elif locator == 'tap2':
        #     print(f"follow(): tap2")
        #     if interactive:
        #         hit_enter_to_continue(helper=helper)
        #     if not dryrun:
        #         print(f"element = {element}")
        #         print(f"element.id = {element.id}")
        #         tap2(driver, element, **opt)
        #         ret['Success'] = True
        else:
            raise RuntimeError(f"unsupported 'cmd={cmd}'")

        return ret

    def locate_dict(self, step: dict, **opt) -> dict:
        '''
        locate_dict() is not called directly in this file.
        it is a component of locate() in locatetools_new.py
        '''
        ret = tpsup.locatetools_new.ret0.copy()
        ret['Success'] = False
        
        raise NotImplementedError("locate_dict() is not implemented yet")

# driverEnv: Union[AppiumEnv, None] = None

# def get_driverEnv(**args) -> AppiumEnv:
#     global driverEnv

#     if not driverEnv:
#         driverEnv = AppiumEnv(**args)
#     return driverEnv

# def get_driver(**args) -> webdriver.Remote:
#     global driver

#     if not driver:
#         driverEnv = get_driverEnv(**args)
#         driver = driverEnv.get_driver()
#     return driver

# def get_emulator(**args) :
#     global driverEnv

#     if not driverEnv:
#         driverEnv = AppiumEnv(**args)
#     return driverEnv.get_emulator()





def dump(driver: webdriver.Remote, element: WebElement, scope: str, path: str, **opt):
    verbose = opt.get('verbose', False)

    if scope == 'element':
        if path == 'stdout':
            output_filename = '-'
        else:
            output_filename = f"{path}/element.txt"

        with tpsup.filetools.TpOutput(output_filename) as fh:
            if re.match(r'webview', driver.current_context, re.IGNORECASE):
                html = element.get_attribute('outerHTML')
                fh.write(html)
                fh.write('\n')
            else:
                # dump native element
                for attr in ['text', 'content-desc', 'resource-id', 'id', 'outerHTML']:
                    value = None
                    try:
                        value = element.__getattribute__(attr)
                    except Exception as e:
                        if verbose:
                            print(
                                f"dump(): element.__getattribute__('{attr}') failed with exception={e}")
                    fh.write(f"{attr}={value}\n\n")
    else:
        # scope == 'page
        if path == 'stdout':
            output_filename = '-'
        else:
            output_filename = f"{path}/page.txt"

        with tpsup.filetools.TpOutput(output_filename) as fh:
            fh.write(driver.page_source)
            fh.write('\n')

    if path != 'stdout':
        with tpsup.filetools.TpOutput(f"{path}/contexts.txt") as fh:
            fh.write(f"{driver.contexts}")
            fh.write('\n')
            fh.close()
        with tpsup.filetools.TpOutput(f"{path}/current_context.txt") as fh:
            fh.write(f"{driver.current_context}")
            fh.write('\n')
            fh.close()
    else:
        print("------------- contexts ---------------")
        print(f"{driver.contexts}")
        print("")
        print("------------- current_context ---------------")
        print(f"{driver.current_context}")
        print("")


# def tap2(driver: webdriver.Remote, element: WebElement, **opt):
#     verbose = opt.get('verbose', False)

#     location = element.location  # (0, 0) is the top left corner of the element
#     size = element.size  # (width, height) of the element

#     # get element's center
#     x = location['x'] + size['width'] / 2
#     y = location['y'] + size['height'] / 2
#     # action = TouchAction(driver)
#     actions = ActionChains(driver)


#     i = 0
#     max = 9
#     while i < max:
#         i += 1
#         print(f"doubleclick: try {i}/{max}")

#         if i % 3 == 1:
#             action.tap2(x=x, y=y, wait=100).perform()
#         elif i % 3 == 2:
#             action.tap2(x=x, y=y, wait=175).perform()
#         else:
#             action.tap2(x=x, y=y, wait=250).perform()

#         print(f"sleep 3 seconds before check")
#         time.sleep(3)
#         try:
#             # (0, 0) is the top left corner of the element
#             location = element.location
#         except Exception as e:
#             if verbose:
#                 print(
#                     f"cannot find element location any more, meaning previous tap worked: {e}")
#             break

#         print(f"sleep 3 seconds before next try")
#         time.sleep(3)


def doubleclick(driver: webdriver.Remote, element: WebElement, **opt):
    verbose = opt.get('verbose', False)

    location = element.location  # (0, 0) is the top left corner of the element
    size = element.size  # (width, height) of the element

    # get element's center
    x = location['x'] + size['width'] / 2
    y = location['y'] + size['height'] / 2
    # action = TouchAction(driver)
    actions = ActionChains(driver)

    actions.double_click(element).perform()

def swipe(driver: webdriver.Remote, param: str, **opt):
    '''
    param: direction,distance
    direction is one of up, down, left, right.
    size is small, medium, large, default is medium.
    examples: 
        up    # default size is medium
        down,small
        small,down
        left,large
    '''

    # check param
    if not param:
        raise RuntimeError("swipe: param is empty")
    param = param.lower()
    
    window_size = driver.get_window_size()
    width = window_size['width']
    height = window_size['height']
    print(f"swipe: window_size={window_size}")


    if 'small' in param:
        size='small'
        size_factor = 0.55
    elif 'large' in param:
        factor = 0.9
    else:
        size='medium'
        # medium or unspecified, the default, a little less than 1 page
        size_factor = 0.7

    # top-left corner is (0, 0)
    if 'up' in param:
        direction = 'up'
        from_x = width * 0.5
        from_y = height * size_factor
        to_x = width * 0.5
        to_y = height * (1 - size_factor)
    elif 'down' in param:
        direction = 'down'
        from_x = width * 0.5
        from_y = height * (1 - size_factor)
        to_x = width * 0.5
        to_y = height * size_factor
    elif 'left' in param:
        direction = 'left'
        from_x = width * size_factor
        from_y = height * 0.5
        to_x = width * (1 - size_factor)
        to_y = height * 0.5
    elif 'right' in param:
        direction = 'right'
        from_x = width * (1 - size_factor)
        from_y = height * 0.5
        to_x = width * size_factor
        to_y = height * 0.5
    else:
        raise RuntimeError(f"invalid swipe param={param}, missing direction")

    print(f"swipe: window width={width}, height={height}, swipe param={param}, \n",
          f"       direction={direction}, size={size}, size_factor={size_factor}\n",
          f"       from ({from_x},{from_y}) to ({to_x},{to_y})")
    driver.swipe(from_x, from_y, to_x, to_y, 800)
    



procs = [
            "qemu-system-x86_64.exe", 
            # emulator
            # C:\Users\tian>ps -ef |grep qemu-system-x86_64.exe
            # 1/25/2025 7:49:52 PM      21612 C:\Users\tian\AppData\Local\Android\Sdk\emulator\qemu\windows-x86_64\qemu-system-x86_64.exe -netdelay none -netspeed full -avd myemulator -port 5554

            "node.exe",  
            # appium server
            # C:\Users\tian>ps -ef |grep node.exe
            # 1/25/2025 7:49:56 PM      10056 C:\tools\nodejs\node.exe C:\tools\nodejs\node_modules\appium\build\lib\main.js --address 127.0.0.1 --port 4723 --log-no-colors --base-path /wd/hub --log C:/Users/tian/appium\appium.log --log-level debug

            "adb", 
            # adb server
            # C:\Users\tian>ps |grep adb
            # 1/25/2025 7:50:52 PM       1936 adb -L tcp:5037 fork-server server --reply-fd 560

            "chromedriver", 
            # chromedriver
            # we need chromedriver when we want to use webview
        ]


# the following is for batch framework - batch.py
#
# pre_batch and post_batch are used to by batch.py to do some setup and cleanup work
# '
# known' is only available in post_batch, not in pre_batch.

def pre_batch(all_cfg, known, **opt):
    # init global variables.
    # AppiumEnv class doesn't need global vars because it is Object-Oriented
    # but batch.py uses global vars to shorten code which will be eval()/exec()
    # global driverEnv

    log_FileFuncLine(f"running pre_batch()")
    if all_cfg["resources"]["appium"].get('driverEnv', None) is None:
        # driverEnv is created in delayed mode
        method = all_cfg["resources"]["appium"]["driver_call"]['method']
        kwargs = all_cfg["resources"]["appium"]["driver_call"]["kwargs"]
        # driverEnv = method(**{**kwargs, "dryrun": 0, **opt})  # overwrite kwargs
        driverEnv = method(**{**kwargs, **opt})  # overwrite kwargs
        # 'host_port' are in **opt
        all_cfg["resources"]["appium"]["driverEnv"] = driverEnv
        log_FileFuncLine(f"driverEnv is created in batch.py's delayed mode")

def post_batch(all_cfg, known, **opt):
    dryrun = opt.get("dryrun", 0)

    print("")
    print("--------------------------------")
    
    if dryrun:
        print(f"dryrun, skip post_batch()")
        return
    
    print(f"running post_batch()")

    driverEnv:AppiumEnv = None
    try: 
        driverEnv = all_cfg["resources"]["appium"]["driverEnv"]
    except Exception as e:
        print(f"driverEnv is not created, skip cleanup")
        return
    if driverEnv and driverEnv.driver:
        print(f"driver is still alive, quit it")
        driverEnv.driver.quit()

    # no need to close driverEnv because it it doesn't have much resource to close

    # don't kill procs because it takes too long to restart emulator and appium server.
    # log_FileFuncLine(f"kill chromedriver if it is still running")
    # tpsup.pstools.kill_procs(procs, **opt)

    tpsup.pstools.check_procs(procs, **opt)


tpbatch = {
    # used by batch.py
    'pre_batch': pre_batch,
    'post_batch': post_batch,
    'extra_args': {
        # argparse's args
        'host_port': {
            'switches': ['-hp', '-host_port'],
            'default': 'localhost:4723',
            'action': 'store',
            'help': 'host and port of appium sever',
        },
        'headless': {
            'switches': ['-headless'],
            'default': False,
            'action': 'store_true',
            'help': 'run in headless mode',
        },
        'is_emulator': {
            'switches': ['-emu', '-is_emulator'],
            'default': False,
            'action': 'store_true',
            'help': 'this is emulator, therefore, auto start it if it is not running',
        },
        'js': {
            'switches': ['-js'],
            'default': False,
            'action': 'store_true',
            'help': 'run js'
        },
        'trap': {
            'switches': ['-trap'],
            'default': False,
            'action': 'store_true',
            'help': 'used with -js, to add try{...}catch{...}',
        },
        'full': {
            'switches': ['-full'],
            'default': False,
            'action': 'store_true',
            'help': 'print full xpath in levels, not shortcut, eg. /html/body/... vs id("myinput")',
        },
        'limit_depth': {
            'switches': ['-limit_depth'],
            'default': 5,
            'action': 'store',
            'type': int,
            'help': 'limit scan depth',
        },
        'humanlike': {
            "switches": ["--humanlike"],
            "default": False,
            "action": "store_true",
            "help": "add some random delay to make it more humanlike",
        },
        'kill': {
            "switches": ["--kill"],
            "default": False,
            "action": "store_true",
            "help": f"kill {procs}",
        },
    },
    'resources': {
        'appium': {
            # 'method': get_driver,
            'method': AppiumEnv, 
            'cfg': {
                # 'host_port': 'auto'
            },
            # we delay the driver init till we really need it.
            'init_resource': 0,
        },
    },
}


def main():
    driverEnv = AppiumEnv(host_port='localhost:4723', is_emulator=True)
    driver = driverEnv.start_driver()

    print(f"click home button")


    # https://developer.android.com/reference/android/view/KeyEvent#KEYCODE_ENTER
    driver.press_keycode(3)

    print(f"sleep 15 seconds")
    time.sleep(15)

    myenv = tpsup.envtools.Env()
    home_dir = myenv.home_dir
    with open(f"{home_dir}/page_source.hml", 'w') as fh:
        fh.write(driver.page_source)
        fh.write('\n')
        fh.close()

    # <android.widget.TextView index="1" package="com.android.quicksearchbox"
    # class="android.widget.TextView" text=""
    # resource-id="com.android.quicksearchbox:id/search_widget_text"
    # checkable="false" checked="false" clickable="true" enabled="true"
    # focusable="true" focused="false" long-clickable="false" password="false"
    # scrollable="false" selected="false" bounds="[143,130][664,217]" displayed="true" />
    # https://appium.io/docs/en/commands/element/find-elements/
    # search_element \
    #     = driver.find_element(AppiumBy.XPATH,
    #                           # '//*[@id="screenshotContainer"]/div[2]/div/div/div/div/div[20]/div'
    #                           # '/html/body/div/div/div/div/div[2]/div[1]/div[2]/div/div/div/div/div[20]/div'
    #                             '/html/body/div[1]/div/div/div/div[2]/div[1]/div[2]/div/div/div/div/div[20]'
    #                           )

    print("finding element")
    search_element = driver.find_element(
        AppiumBy.ID, "com.android.quicksearchbox:id/search_widget_text")
    print("clicking element")
    search_element.click()
    print("sleeping 15 seconds")
    time.sleep(15)

    # <android.widget.EditText index="0" package="com.android.quicksearchbox"
    # class="android.widget.EditText" text=""
    # resource-id="com.android.quicksearchbox:id/search_src_text"
    # checkable="false" checked="false" clickable="true" enabled="true"
    # focusable="true" focused="true" long-clickable="true" password="false"
    # scrollable="false" selected="false" bounds="[0,61][712,148]" displayed="true" />
    print("finding element again")
    search_element = driver.find_element(
        AppiumBy.ID, "com.android.quicksearchbox:id/search_src_text")
    print("clicking element again")
    search_element.click()
    print("typing keys")
    search_element.send_keys('Amazon')
    print("clicking search")
    driver.execute_script('mobile: performEditorAction', {'action': 'Search'})

    print("sleep 15 seconds")
    time.sleep(15)

    # <android.view.View index="9" package="org.chromium.webview_shell" class="android.view.View"
    # text="" content-desc="Amazon Home &amp; Kitchen" checkable="false" checked="false"
    # clickable="true" enabled="true" focusable="true" focused="false" long-clickable="false"
    # password="false" scrollable="false" selected="false" bounds="[32,1118][688,1184]" displayed="true">
    print("parse result")
    target_attr = "content-desc"
    elements = driver.find_elements(
        AppiumBy.XPATH, f"//*[@{target_attr}]")  # attr existence
    for e in elements:
        print(f"{e.get_attribute(target_attr)}")

    interval = 5
    print(f"sleep {interval} seconds")
    time.sleep(interval)

    print("quiting")
    driver.quit()


if __name__ == "__main__":
    main()
