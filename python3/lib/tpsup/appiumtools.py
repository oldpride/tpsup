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

import tpsup.locatetools
from tpsup.logbasic import log_FileFuncLine
from tpsup.nettools import is_tcp_open, wait_tcps_open
import tpsup.pstools
import tpsup.seleniumtools
import tpsup.tmptools
from tpsup.human import human_delay
import os.path
from tpsup.logtools import tplog
from tpsup.utilbasic import hit_enter_to_continue
from tpsup.exectools import exec_into_globals, multiline_eval

from typing import List, Union
from pprint import pformat

diagarm = '''
                         host_port   adb_device_name  phone/emulator
    +----------+       +----------+      +------+    +---------------+
    | appium   +------>+ appium   +----->+ adb  +--->+ adbd          |
    | python   |       | server   | adb  |server|    |               |
    | webdriver|       | Nodejs   | cmd  +------+    |               +---->internet
    |          |       |          |                  | UIAutomator2. |
    |          |       |          |----------------->| Bootstrap.jar  |
    |          |       |          |     HTTP  W3C    | runs a TCP    |
    |          |       |          |                  | listening port|
    +----------+       +----------+                  +---------------+    
    
    host_port is appium sever's host and port.
    adb_device_name is what command "adb devices" shows.
'''

driver: webdriver.Remote = None # not webdriver.Chrome!
# we use this to control both explicit and implicit wait. 
# more detail about explicit and implicit wait, see other comments in this file.
wait_seconds = 10 # seconds

# "last_element" is the last element we concerned.
# note: this may not be the active element. For example, if the previous step
# used xpath to find an element, the element is the "last_element", but only
# if we click on it, it become active.
# however, if we just want to get attribute or dump the element, we can just
# use the "last_element".
last_element = None

# run these locators before or after each step
debuggers = {
    'before': [],
    'after': [],
}

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
            host_port = 'localhost:4723'

    (host, port) = host_port.split(":", 1)
    if is_tcp_open(host, port):
        log_FileFuncLine(f"{proc}_host_port={host_port} is already open")
        return {'status': 'already running', 'error': 0}
    else:
        log_FileFuncLine(f"{proc}_host_port={host_port} is not open")

    if host.lower() != "localhost" and host != "127.0.0.1" and host != "":
        log_FileFuncLine(f"we cannot start remote {proc}")
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
        # andorid studio -> virtual device manager -> select emulator -> edit -> name it to below
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
            subprocess.Popen(
                cmd, shell=True, stderr=subprocess.STDOUT, stdout=log_ofh)
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
        self.env = tpsup.envtools.Env()
        self.env.adapt()
        home_dir = os.path.normpath(
            self.env.home_dir)  # get_native_path() is for cygwin
        self.log_base = opt.get('log_base', f"{home_dir}/appium")

        # self.page_load_timeout = opt.get('page_load_timeout', 30)
        self.dryrun = opt.get("dryrun", False)

        self.emulator_log = os.path.join(self.log_base, "emulator.log")
        self.appium_log = os.path.join(self.log_base, "appium.log")

        if clean or cleanQuit:
            self.clean()
            if cleanQuit:
                exit(0)

        self.is_emulator = is_emulator
        need_wait = []
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
        
        log_FileFuncLine(f"capabilities = {pformat(self.capabilities)}")
        # https://www.youtube.com/watch?v=h8vvUcLo0d0

        log_FileFuncLine(f"driverEnv is created. driver will be created when needed by calling driverEnv.get_driver()")

        # we only set up driverEnv, not initializing driver.
        # we initialize driver when get_driver() is called on demand.

    def get_driver(self) -> webdriver.Remote:
        need_wait = []

        if self.is_emulator:
            print()
            print(f"starting emulator if not already started")
            response = start_proc('emulator', log=self.emulator_log, **self.opt)
            log_FileFuncLine(f"emulator response = {pformat(response)}")
            if response.get('status', None) == "started":
                need_wait.append(response.get("host_port"))

        print()
        print(f"starting appium server if not already started")
        response = start_proc('appium', log=self.appium_log, base_path=self.base_path, **self.opt)
        log_FileFuncLine(f"appium response = {pformat(response)}")
        self.service: AppiumService = response.get('service', None)
        if response.get('status', None) == "started":
            need_wait.append(response.get("host_port"))

        if need_wait:
            proc_wait_seconds = 60
            log_FileFuncLine(f"wait max {proc_wait_seconds} seconds for: {need_wait}")
            if not wait_tcps_open(need_wait, timeout=proc_wait_seconds):
                raise RuntimeError(f"one of port is not ready: {need_wait}")
            
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
    
    def get_home_dir(self) -> str:
        return self.env.home_dir

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

driverEnv: Union[AppiumEnv, None] = None

def get_driverEnv(**args) -> AppiumEnv:
    global driverEnv

    if not driverEnv:
        driverEnv = AppiumEnv(**args)
    return driverEnv

def get_driver(**args) -> webdriver.Remote:
    global driver

    if not driver:
        driverEnv = get_driverEnv(**args)
        driver = driverEnv.get_driver()
    return driver


def locate(locator: str, **opt):
    dryrun = opt.get("dryrun", 0)
    interactive = opt.get("interactive", 0)
    debug = opt.get("debug", 0)
    verbose = opt.get("verbose", debug)
    isExpression = opt.get("isExpression", 0) # for condtion test, we set isExpression=1, so that we get True/False.

    global driver
    global last_element
    global wait_seconds
    global debuggers

    helper = opt.get("helper", {})

    ret = {'Success': False, 'break_levels': 0, 'continue_levels': 0}

    '''
    examples can be found in github test folder
    https://github.com/appium/python-client/tree/master/test
    '''

    if m := re.match(r"(start_driver|driver)$", locator):
        print(f"locate: start driver")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            driver = get_driver(**opt)
            # update_locator_driver(**opt)
            ret['Success'] = True
    elif m := re.match(r"kill_procs$", locator):   
        print(f"locate: kill_procs: {procs}")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            tpsup.pstools.kill_procs(procs)
            ret['Success'] = True
    elif m := re.match(r"check_procs$", locator):   
        print(f"locate: check_procs: {procs}")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            tpsup.pstools.check_procs(procs)
            ret['Success'] = True
    elif m := re.match(r"installapp=(.+)$", locator, flags=re.IGNORECASE):
        app, *_ = m.groups()
        print(f"locate: installapp={app}")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            if not driver:
                driver = get_driver(**opt)
            driver.install_app(app)
            ret['Success'] = True
    elif m := re.match(r"(existsapp|removeapp)=(.+)$", locator, flags=re.IGNORECASE):
        action, app, *_ = m.groups()
        print(f"locate: {action}={app}")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            if not driver:
                driver = get_driver(**opt)
            if action == 'existsapp':
                ret['Success'] = driver.is_app_installed(app)
            else:
                driver.remove_app(app)
                ret['Success'] = True

    elif m := re.match(r"\s*(xpath|css|id)=(.+)", locator):
        tag, value, *_ = m.groups()
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
        print(f"follow(): {tag}={value}")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if dryrun:
            if tag == 'xpath':
                print(f"validate xpath={value}")
                lxml.etree.XPath(value)
        else:
            if not driver:
                driver = get_driver(**opt)
            if tag == 'id':
                element = driver.find_element(AppiumBy.ID, value)
            elif tag == 'xpath':
                element = driver.find_element(AppiumBy.XPATH, value)
            elif tag == 'css':
                element = driver.find_element(AppiumBy.CSS_SELECTOR, value)

            last_element = element
            ret['Success'] = True
    elif m := re.match(r"sleep=(\d+)", locator):
        value, *_ = m.groups()
        print(f"follow(): sleep {value} seconds")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            time.sleep(int(value))      
            ret['Success'] = True
    elif m := re.match(r"(impl|expl|script|page)*wait=(\d+)", locator):
        # implicit wait
        wait_type, value, *_ = m.groups()
        if not wait_type:
            wait_type = 'all'
        print(f"locate: set {wait_type} wait type to {value} seconds")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            if wait_type == 'all' or wait_type == 'expl':
                # explicit wait is set when we call WebDriverWait(driver, wait_seconds).
                # explicit wait is done per call (WebDriverWait()).
                # As we are not calling WebDriverWait() here, we only set the global variable,
                # so that it can be used when we call WebDriverWait() in the future.
                wait_seconds = int(value)

            if wait_type == 'all' or wait_type == 'impl':
                # driver.implicitly_wait() only set the implicit wait for the driver, 
                # affect all find_element() calls right away.
                # implicit wait is done once per session (driver), not per call.
                # selenium's default implicit wait is 0, meaning no wait.
                driver.implicitly_wait(wait_seconds)

            if wait_type == 'all' or wait_type == 'script':
                # set script timeout
                driver.set_script_timeout(int(value))

            if wait_type == 'all' or wait_type == 'page':
                # set page load timeout
                '''
                this for chromedriver; other driver use implicitly_wait()
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
                driver.set_page_load_timeout(int(value))
            ret['Success'] = True
    # elif m := re.match(r"(home|enter|backspace)$", locator, re.IGNORECASE):
    #     value, *_ = m.groups()
    #     print(f"follow(): {value}")
    #     locate(f"sendkey={value}", **opt)
    #     ret['Success'] = True
    elif m := re.match(r"sendkey=(.+)", locator, re.IGNORECASE):
        value, *_ = m.groups()
        print(f"follow(): sendkey={value}")

        value = value.upper()
        # https://stackoverflow.com/questions/74188556
        androidkey = nativekey.AndroidKey

        keycode = androidkey.__dict__.get(value, None)
        if not keycode:
            raise RuntimeError(f"key={value} is not supported")
        
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            if debug:
                print(f"key={value}, keycode={keycode}")

            # selenium's send_keys is element.send_keys(), using the element as the target.
            # appium's send_keys is driver.press_keycode(), using the driver as the target.
            if not driver:
                driver = get_driver(**opt)
            driver.press_keycode(keycode)
            ret['Success'] = True
    elif m := re.match(r"(home|back)$", locator, re.IGNORECASE):
        value, *_ = m.groups()
        print(f"follow(): {value}")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            if not driver:
                driver = get_driver(**opt)
            if value.lower() == 'home':
                driver.press_keycode(nativekey.AndroidKey.HOME)
            elif value.lower() == 'back':
                driver.back()
            # this didn't work
            # elif value.lower == 'appswitch':
            #     driver.press_keycode(nativekey.AndroidKey.APP_SWITCH)
            ret['Success'] = True

    elif m := re.match(r"string=(.+)", locator, re.MULTILINE | re.DOTALL | re.IGNORECASE):
        value, *_ = m.groups()
        result = locate(f"code2element='''{value}'''", **opt)
        ret['Success'] = result['Success']
    elif m := re.match(r"(code|python|exp|js)(file)?(.*?)=(.+)", locator, re.MULTILINE | re.DOTALL):
        '''
        'code' and 'python' are the same - python code to be executed.
        'exp' is python code which returns True/False or equivalent (eg, 1 vs 0, "abc" vs "").
        examples
            code=print("hello world")
            python=print("hello world")
            exp=i==1
            js=console.log("hello world")
            jsfile=filename.js
            code2print="1+1"
            codefile=filename.py
            jsfile2element=filename.js
            js2element="return document.querySelector('body')"
        '''
        # directive, code, *_ = m.groups()
        lang, file, target, code, *_ = m.groups()

        if file:
            print(f"locate: read {lang} from file {code}")
            with open(code) as f:
                code = f.read()
        else:
            print(f"locate: run {lang}: {code}")

        # parse 'target'
        if target:
            if m := re.match(r"2(print|pformat|element)+$", target):
                target = m.group(1)
            else:
                raise RuntimeError(f"unsupported target={target}")
           
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
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
                                element = driver.switch_to.active_element
                                element.send_keys(result)
                                last_element = element
                            elif 'print' in target:
                                print(result)
                            elif 'pformat' in target:
                                print(pformat(result))
                            else:
                                raise RuntimeError(f"lang={lang} doesn't support target={target}.")
                            # note 'result' could be a empty string, which is False in python.
                            # therefore we don't use 'result' to set ret['Success']
                            ret['Success'] = True
                        else:
                            ret['Success'] = result
                else:
                    exec_into_globals(code, globals(), locals())
                    ret['Success'] = True # hard code to True for now               
            elif lang == 'js':
                jsr = driver.execute_script(code)
                if debug:
                    print(f"locate: jsr={pformat(jsr)}") # this is too verbose            
                if 'element' in target:
                    '''
                    jsr can be an element or a dict with possible keys: 
                    element, shadowHost, iframeElement
                    '''
                    if type(jsr) == dict:
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
                        for key in jsr:
                            print(f" {key}={type(jsr[key])}")
                        
                        if "element" in jsr:
                            element = jsr['element']
                            last_element = element
                                            
                    elif isinstance(jsr, WebElement):
                        # jsr is an instance of element
                        print(f'locate: jsr={type(jsr)}')
                        last_element = jsr
                    else:
                        print(f"locate: jsr is not an element nor a dict, but {type(jsr)}")
                        last_element = driver.switch_to.active_element
                else:
                    print(f"locate: jsr={pformat(jsr)}") # this is too verbose
                    last_element = driver.switch_to.active_element

                if 'print' in target:
                    print(jsr)
                
                # https://stackoverflow.com/questions/37791547
                # https://stackoverflow.com/questions/23408668
                # last_iframe = driver.execute_script("return window.frameElement")
                # # pause to confirm
                # print(f"last_iframe={last_iframe}")
                # hit_enter_to_continue(helper=helper)

                ret['Success'] = True
    elif m := re.match(r"dump_(page|element)=(.+)", locator):
        scope, path, *_ = m.groups()
        print(f"follow(): dump {scope} to dir={path}")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            # print(f"before dump, element.__getattribute__('id') = {element.__getattribute__('id')}")
            dump(driver, last_element, scope, path, verbose=verbose)
            ret['Success'] = True
    # elif m := re.match(r"action=(Search)", locator):
    #     value, *_ = m.groups()
    #     print(f"follow(): perform action={value}")
    #     if interactive:
    #         hit_enter_to_continue(helper=helper)
    #     if not dryrun:
    #         driver.execute_script(
    #             'mobile: performEditorAction', {'action': value})
    #         ret['Success'] = True
    elif m := re.match(r"context=(native|webview)", locator):
        value, *_ = m.groups()
        print(f"follow(): switch to context matching {value}")

        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            contexts = driver.contexts
            context = None
            for c in contexts:
                if value == 'native':
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
            driver.switch_to.context(context)
            ret['Success'] = True
    elif locator == 'click':
        print(f"follow(): click")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            last_element.click()
            ret['Success'] = True
    elif locator == 'doubleclick':
        print(f"follow(): doubleclick")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            print(f"element = {element}")
            print(f"element.id = {element.id}")
            doubleclick(driver, element, **opt)
            ret['Success'] = True
    # elif locator == 'tap2':
    #     print(f"follow(): tap2")
    #     if interactive:
    #         hit_enter_to_continue(helper=helper)
    #     if not dryrun:
    #         print(f"element = {element}")
    #         print(f"element.id = {element.id}")
    #         tap2(driver, element, **opt)
    #         ret['Success'] = True
    elif locator == 'refresh':
        print(f"follow(): refresh driver")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            driver.refresh()
            ret['Success'] = True
    elif m := re.match(r"run=(.+?)/(.+)", locator, re.IGNORECASE):
        pkg, activity, *_ = m.groups()
        print(f"follow(): run pkg='{pkg}', activity='{activity}'")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            if not driver:
                driver = get_driver(**opt)
            driver.execute_script(
                'mobile: startActivity',
                {
                    'component': f'{pkg}/{activity}',
                },
            )
            ret['Success'] = True

    elif m := re.match(r"swipe=(.+)", locator):
        param, *_ = m.groups()
        print(f"follow(): swipe {param}")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            swipe(driver, param, **opt)
    elif m := re.match(r"debug_(before|after)$", locator):
        '''
        "debug_before" vs "debug_before=step1,step2"

        "debug_before", ie, without steps, is to execute all debuggers['before'].
        "debug_before=step1,step2" is to update debuggers['before'], not execute them.
        '''
        ret['Success'] = True # hard code to True for now

        before_after, *_ = m.groups()

        if not dryrun:
            for step in debuggers[before_after]:
                # we don't care about the return value but we should avoid
                # using locator (step) that has side effect: eg, click, send_keys
                print(f"follow: debug_{before_after}={step}")
                locate(step, **opt)
    elif m := re.match(r"(print|debug(?:_before|_after)*)=((?:(?:\b|,)(?:currentActivity|css|element|tag|text|title|timeouts|url|waits|xpath))+)$", 
                       locator, flags=re.IGNORECASE):
        '''
        (?...) is non-capturing group. therefore, there are only 2 capturing groups in above regex,
        and both are on outside.
        debug_before=url,title,tag => group 1 = debug_before, group 2 = url,title,tag

        examples:
            print=text,tag
        '''
        ret['Success'] = True
        directive, keys_string = m.groups()
        keys = keys_string.split(",")
        '''
        directive: 'print' vs 'debug...'
            'print' is excuted right here and only once.
            'debug' is saved in debuggers[] and executed later, before or after each locate() call.
        '''
        if directive == 'print':
            print(f"locate: print {keys}")
            if not dryrun:
                for key in keys:
                    if not dryrun:
                        if not driver:
                            driver = get_driver(**opt)
                        if key.lower() == 'currentactivity':
                            current_activity = driver.current_activity
                            print(f'current_activity={current_activity}')
                        elif key.lower() == 'html':
                            if last_element:
                                html = last_element.get_attribute('outerHTML')
                                print(f'element_html=element.outerHTML={html}')   
                            else:
                                print(f'element_html is not available because last_element is None')
                        elif key.lower() == 'tag':
                            # get element type
                            if last_element:
                                tag = last_element.tag_name
                                print(f'element_tag_name=element.tag_name={tag}')
                        elif key.lower() == 'text':
                            if last_element:
                                text = last_element.text
                                print(f'element.text={text}')
                        elif key.lower() == 'title':
                            title = driver.title
                            print(f'driver.title={title}')
                        elif key.lower() == 'timeouts' or key == 'waits':
                            # https://www.selenium.dev/selenium/docs/api/py/webdriver_chrome/selenium.webdriver.chrome.webdriver.html
                            # https://www.selenium.dev/selenium/docs/api/java/org/openqa/selenium/WebDriver.Timeouts.html
                            print(f'    explicit_wait={wait_seconds}')    # we will run WebDriverWait(driver, wait_seconds)
                            print(f'    implicit_wait={driver.timeouts.implicit_wait}') # when we call find_element()
                            print(f'    page_load_timeout={driver.timeouts.page_load}') # driver.get()
                            print(f'    script_timeout={driver.timeouts.script}') # driver.execute_script()
                        elif key.lower() == 'url':
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
                            if last_element:
                                # the following are the same
                                # element_url = driver.execute_script("return arguments[0].src", last_element)
                                element_url = last_element.get_attribute('src')

                                print(f'    element_url=element.get_attribute("src")={element_url}')
                            else:
                                print(f'    element_url is not available because last_element is None')

                            # https://stackoverflow.com/questions/938180
                            iframe_url = driver.execute_script("return window.location.href")
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
                            driver_url = driver.current_url
                            print(f'    driver_url=driver.current_url={driver_url}')

                            # https://stackoverflow.com/questions/938180
                            parent_url = driver.execute_script("return document.referrer")
                            print(f'    parent_iframe_url=document.referrer={parent_url}')
                        elif key.lower() == 'xpath':
                            print("xpath is not implemented yet")
                        #     if last_element:
                        #         xpath = js_get(last_element, 'xpath', **opt)
                        #         print(f'element_xpath={xpath}')
                        #     else:
                        #         print(f'element_xpath is not available because last_element is None')
        else:
            # now for debugs
            if directive == 'debug_before':
                before_after = 'before'
            else:
                # directive == 'debug_after' or directive == 'debug'
                before_after = 'after'

            print(f"locate: set debug_{before_after}={keys_string}")

            if not dryrun:
                action = f"print={keys_string}"
                debuggers[before_after] = [action]
                print(f"locate: debuggers[{before_after}]={pformat(debuggers[before_after])}")
    else:
        raise RuntimeError(f"unsupported 'locator={locator}'")

    return ret


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
    window_size = driver.get_window_size()
    width = window_size['width']
    height = window_size['height']
    print(f"swipe: window_size={window_size}")

    # actions = TouchAction(driver)
    # actions = ActionChains(driver)

    if 'small' in param:
        factor = 0.55
    elif 'large' in param:
        factor = 0.9
    else:
        # default, a little less than 1 page
        factor = 0.7

    # top-left corner is (0, 0)
    if 'up' in param:
        driver.swipe(width * 0.5, height * factor,
                     width * 0.5, height(1 - factor))
    elif 'down' in param:
        driver.swipe(width * 0.5, height * (1 - factor),
                     width * 0.5, height * factor)
    elif 'left' in param:
        driver.swipe(width * factor, height * 0.5,
                     width * (1 - factor), height * 0.5)
    elif 'right' in param:
        driver.swipe(width * (1 - factor), height *
                     0.5, width * factor, height * 0.5)


procs = [
            "qemu-system-x86_64.exe", # emulator
            "node.exe",  # appium server
            "adb.exe", # adb server
            "chromedriver", # chromedriver
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
    global driverEnv

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

    if driver:
        print(f"driver is still alive, quit it")
        driver.quit()

    # no need to close driverEnv because it it doesn't have much resource to close

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
            'switches': ['-is_emulator'],
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
    driver = driverEnv.get_driver()

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
