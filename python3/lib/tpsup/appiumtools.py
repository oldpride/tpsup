import os
import re
import subprocess
import sys
import time
from urllib.parse import urlparse
from shutil import which

from appium import webdriver

from appium.webdriver.appium_service import AppiumService
from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver import WebElement

import tpsup.env
import tpsup.tpfile

from tpsup.nettools import is_tcp_open, wait_tcps_open
import tpsup.pstools
import tpsup.tptmp
import os.path

from tpsup.util import tplog, hit_enter_to_continue
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
        raise RuntimeError(f"start_process() must be either emulator or appium")

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

    opt2 = {}
    log = opt.get(f'{proc}_log', None)
    if log:
        opt2['stdout'] = opt[f'{proc}_log']

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
        subprocess.Popen(cmd, shell=True, stderr=subprocess.STDOUT, **opt2)
        return {'status': 'started', 'error': 0}
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

            # this is called only when driver.switch_to.context("webview...")
            # it may only work when desired_capacity has "app" set
            # https://github.com/appium/appium-inspector/issues/465
            # otherwise, error: unrecognized chrome option: androidDeviceSerial
            "--chromedriver-executable", r"C:\Users\william\appium\bin\chromedriver108.exe",
        ]
        # f"--log={self.appium_log}"

        print(f"starting cmd = appium {' '.join(args)}")
        service.start(args=args)
        print(f"service.is_running={service.is_running}")
        print(f"service.is_listening={service.is_listening}")
        # service.stop()
        return {'status': 'started', 'error': 0, 'service': service}


class AppiumEnv:
    def __init__(self, adb_devicename: str, host_port: str, **opt):
        self.host_port = host_port
        self.verbose = opt.get("verbose", 0)
        self.env = tpsup.env.Env()
        self.env.adapt()
        home_dir = tpsup.env.get_native_path(self.env.home_dir)  # get_native_path() is for cygwin
        self.log_base = opt.get('log_base', f"{home_dir}/appium")

        self.page_load_timeout = opt.get('page_load_timeout', 30)
        self.dryrun = opt.get("dryrun", False)
        self.appium_log = os.path.join(self.log_base, "appium_.log")

        need_wait = 0
        if opt.get('is_emulator', False):
            response = start_proc('emulator', **opt)
            print(f"emulator response = {pformat(response)}")
            if response.get('status', None) == "started":
                need_wait = 1

        appium_exe = which('appium')
        if appium_exe:
            print(f"appium is {appium_exe}")
        else:
            raise RuntimeError(f"appium is not in PATH={os.environ['PATH']}")

        response = start_proc('appium', **opt)
        print(f"appium response = {pformat(response)}")
        self.service: AppiumService = response.get('service', None)
        if response.get('status', None) == "started":
            need_wait = 1

        if need_wait:
            print("wait 60 seconds for appium and/or emulator to start")
            if not wait_tcps_open(['localhost:5554', 'localhost:4723'], timeout=60):
                raise RuntimeError("either emulator or appium server is ready")

        self.driver: webdriver.Remote = None

        self.desired_cap = {
            "appium:deviceName": adb_devicename,
            "appium:platformName": "Android",
        }

        if app := opt.get("app", None):
            self.desired_cap['app'] = app

        if self.verbose:
            print(f"desire_capabilities = {pformat(self.desired_cap)}")
        # https://www.youtube.com/watch?v=h8vvUcLo0d0
        self.driver = webdriver.Remote(f"http://{host_port}/wd/hub", self.desired_cap)
        self.driver.implicitly_wait(60)

        self.driver.Env = self  # monkey patching for convenience

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

def get_driver(**args) -> webdriver.Remote :
    appiumEnv = AppiumEnv(**args)
    return appiumEnv.get_driver()

step_compiled_findby = re.compile(r"\s*(xpath|css|id)=(.+)")
step_compiled_action = re.compile(r"action=(Search)")
step_compiled_string = re.compile(r"string=(.+)", re.MULTILINE | re.DOTALL)
step_compiled_sleep = re.compile(r"sleep=(\d+)")
step_compiled_dump = re.compile(r"dump_(page|element)=(.+)")
step_compiled_context = re.compile(r"context=(native|webview)")
context_compiled_native = re.compile(r'native', re.IGNORECASE)
context_compiled_webview = re.compile(r'webview', re.IGNORECASE)

def follow(driver:webdriver.Remote, steps:list, **opt):
    if not list:
        return

    dryrun = opt.get("dryrun", 0)
    interactive = opt.get("interactive", 0)
    debug = opt.get("debug", 0)
    global we_return
    global action_data

    element:WebElement = None

    helper = {}

    for step in steps:
        if m := step_compiled_findby.match(step):
            tag, value, *_ = m.groups()
            print(f"follow(): {tag}={value}")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                if tag == 'id':
                    element = driver.find_element(AppiumBy.ID, value)
                elif tag == 'xpath':
                    element = driver.find_element(AppiumBy.XPATH, value)
                elif tag == 'css':
                    element = driver.find_element(AppiumBy.CSS_SELECTOR, value)
        elif m := step_compiled_sleep.match(step):
            value, *_ = m.groups()
            print(f"follow(): sleep {value} seconds")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                time.sleep(int(value))
        elif m := step_compiled_string.match(step):
            value, *_ = m.groups()
            print(f"follow(): send_keys={value}")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                element.send_keys(value)
        elif m := step_compiled_dump.match(step):
            scope, path, *_ = m.groups()
            print(f"follow(): dump {scope} to dir={path}")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                if scope == 'element':
                    # https://stackoverflow.com/questions/29671552/
                    # io.appium.uiautomator2.common.exceptions.NoSuchAttributeException:
                    # 'outerHTML' attribute is unknown for the element. Only the
                    # following attributes are supported: [checkable, checked,
                    # {class,className}, clickable, {content-desc,contentDescription},
                    # enabled, focusable, focused, {long-clickable,longClickable},
                    # package, password, {resource-id,resourceId}, scrollable,
                    # selection-start, selection-end, selected, {text,name}, bounds,
                    # displayed, contentSize]
                    html = element.get_attribute('outerHTML')

                else:
                    html = driver.page_source
                if path != 'stdout':
                    with tpsup.tpfile.TpOutput(path) as fh:
                        fh.write(html)
                        fh.write('\n')
                        fh.close()
                else:
                    print(html)
        elif m := step_compiled_action.match(step):
            value, *_ = m.groups()
            print(f"follow(): perform action={value}")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                driver.execute_script('mobile: performEditorAction', {'action': value})
        elif m := step_compiled_context.match(step):
            value, *_ = m.groups()
            print(f"follow(): switch to context matching {value}")
            contexts = driver.contexts
            context = None
            for c in contexts:
                if value == 'native':
                    if m := context_compiled_native.match(c):
                        context = c
                        break
                else:
                    if m := context_compiled_webview.match(c):
                        context = c
                        break
            if context:
                print(f"found context={context} among {pformat(contexts)}")
            else:
                raise RuntimeError(f'no matching context among {pformat(contexts)}')

            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
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
        elif step == 'home':
            print(f"follow(): click home button")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                driver.press_keycode(3)
        else:
            raise RuntimeError(f"unsupported 'step={step}'")

        print(f"follow(): this step is done")


def main():
    appiumEnv = AppiumEnv(adb_devicename='emulator-5558', host_port='localhost:4723', is_emulator=True)
    driver = appiumEnv.get_driver()

    print(f"click home button")
    # https://developer.android.com/reference/android/view/KeyEvent#KEYCODE_ENTER
    driver.press_keycode(3)

    print(f"sleep 15 seconds")
    time.sleep(15)

    myenv = tpsup.env.Env()
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
    search_element = driver.find_element(AppiumBy.ID, "com.android.quicksearchbox:id/search_widget_text")
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
    search_element = driver.find_element(AppiumBy.ID, "com.android.quicksearchbox:id/search_src_text")
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
    elements = driver.find_elements(AppiumBy.XPATH, f"//*[@{target_attr}]")  # attr existence
    for e in elements:
        print(f"{e.get_attribute(target_attr)}")

    interval = 5
    print(f"sleep {interval} seconds")
    time.sleep(interval)

    print("quiting")
    driver.quit()


if __name__ == "__main__":
    main()
