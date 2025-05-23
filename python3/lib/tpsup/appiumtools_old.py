import os
import re
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

# import appium webdriver extensions
import appium.webdriver.extensions.android.nativekey as nativekey
# from appium.webdriver.common.touch_action import TouchAction
# https://stackoverflow.com/questions/75881566/ 
# TouchAction class is being deprecated, and the documentation recommends to use ActionChains

from selenium.webdriver import ActionChains

import tpsup.envtools
import tpsup.filetools

from tpsup.nettools import is_tcp_open, wait_tcps_open
import tpsup.pstools
import tpsup.tmptools
from tpsup.human import human_delay
import os.path
from tpsup.logtools import tplog
from tpsup.utilbasic import hit_enter_to_continue
from tpsup.exectools import exec_into_globals

from typing import List, Union
from pprint import pformat


# appium vs selenium
# +----------+       +----------+      +-----+    +---------+
# | appium   +------>| appium   +----->+ adb +--->+ phone / | +---->internet
# | python   |       | server   |      |     |    | emulator|
# | webdriver|       |GUI/Nodejs|      |     |    |         |
# +----------+       +----------+      +-----+    +---------+
#
# +----------+      +--------------+     +----------------+
# | selenium +----->+ chromedriver +---->+ chrome browser +---->internet
# +----------+      +--------------+     +----------------+


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
        print(f"{proc}_host_port={host_port} is already open")
        return {'status': 'already running', 'error': 0}
    else:
        print(f"{proc}_host_port={host_port} is not open")

    if host.lower() != "localhost" and host != "127.0.0.1" and host != "":
        sys.stderr.write(f"we cannot start remote {proc}\n")
        if opt.get('dryrun', 0):
            sys.stderr.write("this is dryrun, so we continue\n")
            return {'status': 'cannot start', 'error': 1}
        else:
            raise RuntimeError("cannot proceed")

    log = opt.get('log', None)
    if not log:
        log = os.path.expanduser("~") + f"/{proc}.log"

    # https://developer.android.com/studio/run/emulator-commandline
    # https://stackoverflow.com/questions/42604543/launch-emulator-from-appium-python-client
    if proc == 'emulator':
        cmd = f"{os.environ['ANDROID_HOME']}/emulator/emulator -netdelay none -netspeed full " \
              f"-avd myemulator -port {port}"
        if opt.get('headless', False):
            cmd += " -no-window"
        # else:
        #     cmd = f"appium --address localhost -p {port} --log-no-colors"
        #             # f"--log={self.appium_log}","
        print(f"cmd = {cmd}")
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
            "--base-path", '/wd/hub',
            "--log", log,
            "--log-level", "debug",

            # chromedriver
            #   1. this is called only when driver.switch_to.context("webview...")
            #      it may only work when desired_capacity has "app" set
            #      https://github.com/appium/appium-inspector/issues/465
            #      otherwise, error: unrecognized chrome option: androidDeviceSerial
            #   2. chromedriver's version must match chrome version on the device.
            "--chromedriver-executable", r"C:\Users\william\appium\bin\chromedriver108.exe",
        ]
        # f"--log={self.appium_log}"

        print(f"starting cmd = appium {' '.join(args)}")
        service.start(args=args)
        print(f"service.is_running={service.is_running}")
        print(f"service.is_listening={service.is_listening}")
        # service.stop()
        return {
            'status': 'started',
            'error': 0,
            'service': service,
            'host_port': host_port
        }


def get_setup_info():
    return '''
+----------+       +----------+      +-----+    +---------+
| appium   +------>| appium   +----->+ adb +--->+ phone / | +---->internet
| webdrive |       | server   |      |     |    | emulator|
| python   |       |GUI/Nodejs|      |     |    |         |
+----------+       +----------+      +-----+    +---------+

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
    def __init__(self, host_port: str, **opt):
        # host_port is appium server's host and port,
        #   not to be confused with emulator's host and port.
        #   if host_port is not open and host is localhost, this call will start
        #   the appium server at the port.
        # note: we don't need to specify deviceName as shown in 'adb devices' because the
        #   appium server will automatically find the device and
        #   appium only support one device.

        self.host_port = host_port
        self.verbose = opt.get("verbose", 0)
        self.env = tpsup.envtools.Env()
        self.env.adapt()
        home_dir = os.path.normpath(
            self.env.home_dir)  # get_native_path() is for cygwin
        self.log_base = opt.get('log_base', f"{home_dir}/appium")

        self.page_load_timeout = opt.get('page_load_timeout', 30)
        self.dryrun = opt.get("dryrun", False)
        self.appium_log = os.path.join(self.log_base, "appium_.log")

        need_wait = []
        if opt.get('is_emulator', False):
            emulator_log = os.path.join(self.log_base, "emulator.log")
            print(f"emulator_log={emulator_log}")
            response = start_proc('emulator', log=emulator_log, **opt)
            print(f"emulator response = {pformat(response)}")
            if response.get('status', None) == "started":
                need_wait.append(response.get("host_port"))

        appium_exe = which('appium')
        if appium_exe:
            print(f"appium is {appium_exe}")
        else:
            raise RuntimeError(f"appium is not in PATH={os.environ['PATH']}")

        appium_log = os.path.join(self.log_base, "appium.log")
        print(f"appium_log={appium_log}")
        response = start_proc('appium', log=appium_log, **opt)
        print(f"appium response = {pformat(response)}")
        self.service: AppiumService = response.get('service', None)
        if response.get('status', None) == "started":
            need_wait.append(response.get("host_port"))

        if need_wait:
            print(f"wait max 60 seconds for: {need_wait}")
            if not wait_tcps_open(need_wait, timeout=60):
                raise RuntimeError(f"one of port is not ready: {need_wait}")

        self.driver: webdriver.Remote = None

        self.desired_cap = {
            "appium:platformName": "Android",
        }

        if app := opt.get("app", None):
            self.desired_cap['app'] = app  # this actually installs the app

        # these two can be replaced with run=app/activity
        # if appPackage := opt.get("appPackage", None):
        #     self.desired_cap['appPackage'] = appPackage
        #
        # if appActivity := opt.get("appActivity", None):
        #     self.desired_cap['appActivity'] = appActivity

        if self.verbose:
            print(f"desire_capabilities = {pformat(self.desired_cap)}")
        # https://www.youtube.com/watch?v=h8vvUcLo0d0

        self.driver = None
        try:
            self.driver = webdriver.Remote(
                f"http://{host_port}/wd/hub", self.desired_cap)
            # appium implicit wait is default 0. there is no get implicitly_wait() method
            # self.driver.implicitly_wait(60)
        except Exception as e:
            print(f"Exception: {e}")
            print(
                "both appium and device/emulator are running, but webdriver failed to connect")
            print("likely device/emulator is still booting up.")
            sleep_time = 40
            print(f"sleep {sleep_time} seconds and try again")
            time.sleep(sleep_time)

        if not self.driver:
            print("trying again")
            self.driver = webdriver.Remote(
                f"http://{host_port}/wd/hub", self.desired_cap)

        self.driver.driverEnv = self  # monkey patching for convenience

    def get_driver(self) -> webdriver.Remote:
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


def get_driver(**args) -> webdriver.Remote:
    driverEnv = AppiumEnv(**args)
    return driverEnv.get_driver()


def follow(driver: Union[webdriver.Remote, None],  steps: list, **opt):
    if not list:
        return

    interactive = opt.get("interactive", 0)
    debug = opt.get("debug", 0)
    verbose = opt.get("verbose", 0)
    checkonly = opt.get("checkonly", 0)
    humanlike = opt.get("humanlike", 0)

    # dryrun vs checkonly
    dryrun = opt.get("dryrun", 0)
    if checkonly:
        dryrun = 1

    global we_return
    global action_data

    element: WebElement = None

    if (not dryrun) and (not driver):
        raise RuntimeError("driver is None")

    helper = opt.get("helper", {})

    # we support single-level block, just for convenience when testing using appium_steps
    # we don't support nested blocks; for nested block, use python directly
    block = []
    blockend = None
    condition = None
    blockstart = None
    negation = False

    for step in steps:
        # check blockstack empty
        if blockend:
            if step == blockend:
                print(
                    f"matched blockend={blockend}, running block={block}, condition={condition}")
                blockend = None
                if not block:
                    raise RuntimeError(f"block is empty")
                if interactive:
                    hit_enter_to_continue(helper=helper)
                if not dryrun:
                    run_block(driver, blockstart, negation,
                              condition, block, **opt)
                continue
            else:
                block.append(step)
                continue

        if not interactive and not dryrun and humanlike:
            human_delay()

        if m := re.match(r"\s*(while|if)(_not)?=(.+)", step):
            blockstart = m.group(1)
            negation = m.group(2)
            condition = m.group(3)

            if m := re.match(r"\s*(xpath|css|id)=(.+)", condition):
                tag, value, *_ = m.groups()
                if tag == 'id':
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
                    #    element_id = search_widget_text

                    condition = f"driver.find_element(AppiumBy.ID, '''{value}''')"
                elif tag == 'xpath':
                    if checkonly:
                        print(f"check xpath={value}")
                        try:
                            lxml.etree.XPath(value)
                        except lxml.etree.XPathSyntaxError as e:
                            raise RuntimeError(
                                f"XPath syntax error in step={step}: {e}")
                    condition = f"driver.find_element(AppiumBy.XPATH, '''{value}''')"
                elif tag == 'css':
                    condition = f"driver.find_element(AppiumBy.CSS_SELECTOR, '''{value}''')"

            if negation:
                blockend = f"end_{blockstart}{negation}"
            else:
                blockend = f"end_{blockstart}"
            block = []
            print(f"blockstart={blockstart}, negation={negation}, condition={condition}, "
                  f"looking for blockend={blockend}")
            continue

        if m := re.match(r"\s*(xpath|css|id)=(.+)", step):
            tag, value, *_ = m.groups()
            print(f"follow(): {tag}={value}")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if checkonly:
                if tag == 'xpath':
                    print(f"validate xpath={value}")
                    lxml.etree.XPath(value)
            if not dryrun:
                if tag == 'id':
                    element = driver.find_element(AppiumBy.ID, value)
                elif tag == 'xpath':
                    element = driver.find_element(AppiumBy.XPATH, value)
                elif tag == 'css':
                    element = driver.find_element(AppiumBy.CSS_SELECTOR, value)
        elif m := re.match(r"sleep=(\d+)", step):
            value, *_ = m.groups()
            print(f"follow(): sleep {value} seconds")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                time.sleep(int(value))
        elif m := re.match(r"wait=(\d+)", step):
            value, *_ = m.groups()
            print(f"follow(): set implicit wait {value} seconds")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                driver.implicitly_wait(int(value))
        elif m := re.match(r"key=(.+)", step, re.IGNORECASE):
            value, *_ = m.groups()
            value = value.upper()
            print(f"follow(): key={value}")
            # https://stackoverflow.com/questions/74188556
            androidkey = nativekey.AndroidKey
            if interactive:
                hit_enter_to_continue(helper=helper)
            if checkonly:
                print(f"validate key={value}")
                keycode = androidkey.__dict__.get(value, None)
                if not keycode:
                    raise RuntimeError(f"key={value} is not supported")
            if not dryrun:
                keycode = androidkey.__dict__.get(value, None)
                if debug:
                    print(f"key={value}, keycode={keycode}")
                if keycode:
                    driver.press_keycode(keycode)
                else:
                    raise RuntimeError(f"key={value} is not supported")
        elif m := re.match(r"string=(.+)", step, re.MULTILINE | re.DOTALL):
            value, *_ = m.groups()
            print(f"follow(): string={value}")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                element.send_keys(value)
        elif m := re.match(r"dump_(page|element)=(.+)", step):
            scope, path, *_ = m.groups()
            print(f"follow(): dump {scope} to dir={path}")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                # print(f"before dump, element.__getattribute__('id') = {element.__getattribute__('id')}")
                dump(driver, element, scope, path, verbose=verbose)
        elif m := re.match(r"action=(Search)", step):
            value, *_ = m.groups()
            print(f"follow(): perform action={value}")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                driver.execute_script(
                    'mobile: performEditorAction', {'action': value})
        elif m := re.match(r"context=(native|webview)", step):
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
        elif step == 'click':
            print(f"follow(): click")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                element.click()
        elif step == 'doubleclick':
            print(f"follow(): doubleclick")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                print(f"element = {element}")
                print(f"element.id = {element.id}")
                doubleclick(driver, element, **opt)
        elif step == 'tap2':
            print(f"follow(): tap2")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                print(f"element = {element}")
                print(f"element.id = {element.id}")
                tap2(driver, element, **opt)
        elif step == 'refresh':
            print(f"follow(): refresh driver")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                driver.refresh()
        elif m := re.match(r"run=(.+?)/(.+)", step, re.IGNORECASE):
            pkg, activity, *_ = m.groups()
            print(f"follow(): run pkg='{pkg}', activity='{activity}'")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                # https://stackoverflow.com/questions/57644620/
                # driver.launch_app() # launch_app is deprecated
                driver.start_activity(pkg, activity)
                print("launched activity, waiting for 60 seconds for its ready")
                driver.wait_activity(activity, timeout=60)
        elif m := re.match(r"swipe=(.+)", step):
            param, *_ = m.groups()
            print(f"follow(): swipe {param}")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                swipe(driver, param, **opt)
        else:
            raise RuntimeError(f"unsupported 'step={step}'")

        print(f"follow(): this step is done")

    if blockend:
        raise RuntimeError(
            f"mismatched blockend={blockend} at the end of {pformat(steps)}")


def run_block(driver: webdriver.Remote, blockstart: str, negation: str,  condition: str, block: list, **opt):
    # we separate condition and negation because condition test may fail with exception, which is
    # neither True or False.  In this case, we want to know the condition test failed.
    verbose = opt.get('verbose', False)

    if blockstart == 'while':
        while True:
            res = if_block(driver, negation, condition, block, **opt)
            if not res['executed']:
                break
    elif blockstart == 'if':
        if_block(driver, negation, condition, block, **opt)


def if_block(driver: webdriver.Remote, negation: str,  condition: str, block: list, **opt):
    # we separate condition and negation because condition test may fail with exception, which is
    # neither True or False.  In this case, we want to know the condition test failed.

    verbose = opt.get('verbose', False)
    checkonly = opt.get('checkonly', False)

    try:
        passed_condition = eval(condition)
    except Exception as e:
        if verbose:
            print(f"if_block(): condition test failed with exception={e}")
        passed_condition = False

    if passed_condition and negation:
        print(
            f"if_block(): condition '{condition}' is true, but negated, break")
        executed = False
    elif not passed_condition and not negation:
        print(f"if_block(): condition '{condition}' is not true, break")
        executed = False
    else:
        executed = True

    ret = {'executed': executed}

    if executed:
        if not checkonly:
            ret['result'] = follow(driver, block, **opt)

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


def tap2(driver: webdriver.Remote, element: WebElement, **opt):
    verbose = opt.get('verbose', False)

    location = element.location  # (0, 0) is the top left corner of the element
    size = element.size  # (width, height) of the element

    # get element's center
    x = location['x'] + size['width'] / 2
    y = location['y'] + size['height'] / 2
    action = TouchAction(driver)

    i = 0
    max = 9
    while i < max:
        i += 1
        print(f"doubleclick: try {i}/{max}")

        if i % 3 == 1:
            action.tap2(x=x, y=y, wait=100).perform()
        elif i % 3 == 2:
            action.tap2(x=x, y=y, wait=175).perform()
        else:
            action.tap2(x=x, y=y, wait=250).perform()

        print(f"sleep 3 seconds before check")
        time.sleep(3)
        try:
            # (0, 0) is the top left corner of the element
            location = element.location
        except Exception as e:
            if verbose:
                print(
                    f"cannot find element location any more, meaning previous tap worked: {e}")
            break

        print(f"sleep 3 seconds before next try")
        time.sleep(3)


def doubleclick(driver: webdriver.Remote, element: WebElement, **opt):
    verbose = opt.get('verbose', False)

    location = element.location  # (0, 0) is the top left corner of the element
    size = element.size  # (width, height) of the element

    # get element's center
    x = location['x'] + size['width'] / 2
    y = location['y'] + size['height'] / 2
    action = TouchAction(driver)

    i = 0
    max = 10
    while i < max:
        i += 1
        print(f"doubleclick: try {i}/{max}")

        # wait time between taps is critial for double click to work.
        # ideally, the following should work
        #       action.tap(element).wait(100).tap(element).perform()
        # but looking into appium log we see
        #    tap(element) = locate element's (x,y) + tap (x,y)
        # the locate part took extra time. therefore, we locate the element
        # in a separate action, and then tap it in the next action.
        # Because the wait interval is not controllable in wireless debugging, we
        # try different wait intervals to see if it work
        if i % 5 == 4:
            action.tap(x=x, y=y).wait(50).tap(x=x, y=y).perform()
        elif i % 5 == 3:
            action.tap(x=x, y=y).wait(10).tap(x=x, y=y).perform()
        else:
            # the following 2 are the same. They are more likely to succeed due to network latency.
            # action.tap(x=x, y=y).tap(x=x, y=y).perform()
            action.tap(x=x, y=y, count=2).perform()

            # sometimes, even no-wait is not fast enough. the following is from appium server log. we
            # can see no-wait still took about 1 second, because the 2nd tap had to wait for the response
            # from the first tap.
            # 2023-01-01 00:45:15:379 [W3C (0e33c728)] Calling AppiumDriver.performTouch() with args: [[{"action":"tap","options":{"x":551.5,"y":1107,"count":1}},{"action":"tap","options":{"x":551.5,"y":1107,"count":1}}],"0e33c728-8dc6-49b5-82dd-567c1508a410"]
            # 2023-01-01 00:45:15:382 [WD Proxy] Proxying [POST /appium/tap] to [POST http://127.0.0.1:8200/wd/hub/session/448df8e5-309e-4448-bf69-dbfd36602b77/appium/tap] with body: {"x":551.5,"y":1107,"undefined":null}
            # 2023-01-01 00:45:16:256 [WD Proxy] Got response with status 200: {"sessionId":"448df8e5-309e-4448-bf69-dbfd36602b77","value":null}
            # 2023-01-01 00:45:16:259 [WD Proxy] Proxying [POST /appium/tap] to [POST http://127.0.0.1:8200/wd/hub/session/448df8e5-309e-4448-bf69-dbfd36602b77/appium/tap] with body: {"x":551.5,"y":1107,"undefined":null}
            # 2023-01-01 00:45:16:931 [WD Proxy] Got response with status 200: {"sessionId":"448df8e5-309e-4448-bf69-dbfd36602b77","value":null}
            # when it works, i saw the interval was 280 ms
        print(f"sleep 3 seconds before check")
        time.sleep(3)
        try:
            # (0, 0) is the top left corner of the element
            location = element.location
        except Exception as e:
            if verbose:
                print(
                    f"cannot find element location any more, meaning previous tap worked: {e}")
            break

        print(f"sleep 3 seconds before next try")
        time.sleep(3)


def swipe(driver: webdriver.Remote, param: str, **opt):
    window_size = driver.get_window_size()
    width = window_size['width']
    height = window_size['height']
    print(f"swipe: window_size={window_size}")

    actions = TouchAction(driver)

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


def check_proc(**opt):
    for proc in ["qemu-system-x86_64.exe", "node.exe", "adb.exe"]:
        print(f"check if {proc} is still running")
        my_env = tpsup.envtools.Env()
        if tpsup.pstools.ps_grep(f"{proc}", printOutput=1):
            print(f"seeing leftover {proc}")
            # try not to kill it because it takes time to start up
            if opt.get('kill', False):
                if my_env.isWindows:
                    cmd = f"pkill {proc}"
                else:
                    # -f means match the full command line. available in linux, not in windows
                    cmd = f"pkill -f {proc}"
                print(cmd)
                os.system(cmd)


def pre_batch(all_cfg, known, **opt):
    print("")
    print('running pre_batch()')
    driver: webdriver = all_cfg["resources"]["appium"].get("driver", None)
    if driver is None:
        method = all_cfg["resources"]["appium"]["driver_call"]['method']
        kwargs = all_cfg["resources"]["appium"]["driver_call"]["kwargs"]
        driver = method(**{**kwargs, "dryrun": 0, **opt})  # overwrite kwargs
        # 'host_port' are in **opt
        all_cfg["resources"]["appium"]["driver"] = driver
        print("pre_batch(): driver is created")
    print("pre_batch(): done")
    print("--------------------------------")
    print("")


def post_batch(all_cfg, known, **opt):
    print("")
    print("--------------------------------")
    print(f"running post_batch()")
    if 'driver' in all_cfg["resources"]["appium"]:
        print(f"we have driver, quit it")
        driver = all_cfg["resources"]["appium"]["driver"]
        # this is not needed as webdriver is part of this python script, not a separate process.
        driver.quit()
        print("")

        print(f"list all the log files for debug purpose")
        # env vs driverEnv
        #    env is from env.py - no driver info
        #    driverEnv is from AppiumEnv - contains env and driver info
        driverEnv = driver.driverEnv
        my_env = driverEnv.env
        if my_env.isWindows:
            cmd = f"{my_env.ls_cmd} \"{driverEnv.log_base}\\*\""
        else:
            cmd = f"{my_env.ls_cmd} -ld \"{driverEnv.log_base}\"/*"
        print(cmd)
        os.system(cmd)
        print("")

        # delete a key from a dict, we can use either del or pop
        #    se d.pop if you want to capture the removed item, like in item = d.pop("keyA").
        #    Use del if you want to delete an item from a dictionary.
        #        if thekey in thedict: del thedict[thekey]
        del all_cfg["resources"]["appium"]["driver"]

    check_proc(**opt)


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
        'print_console_log': {
            'switches': ['-pcl', '-print_console_log'],
            'default': False,
            'action': 'store_true',
            'help': 'print js console log',
        },
        'limit_depth': {
            'switches': ['-limit_depth'],
            'default': 5,
            'action': 'store',
            'type': int,
            'help': 'limit scan depth',
        },
        'app': {
            'switches': ['-app'],
            'default': None,
            'action': 'store',
            'help': 'app_path, /path/app.apk for android or https://app.com/app.ipa for ios. this copies the package onto device',
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
            "help": "kill the leftover processes in post_batch()",
        },

        # these two can be replaced with run=app/activity
        # {
        #     'dest': 'appPackage',
        #     'default': None,
        #     'action': 'store',
        #     'help': 'appPackage, eg. com.android.chrome',
        # },
        #
        # {
        #     'dest': 'appActivity',
        #     'default': None,
        #     'action': 'store',
        #     'help': 'appActivity, eg. com.android.chrome.Main',
        # }
    },
    'resources': {
        'appium': {
            'method': get_driver,
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
