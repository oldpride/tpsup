import os
import re
import sys
import time
import subprocess
from urllib.parse import urlparse
from shutil import which
import tpsup.cmdtools
import tpsup.envtools
from selenium import webdriver
from tpsup.human import human_delay
import tpsup.logtools
from tpsup.logbasic import log_FileFuncLine

from selenium.common.exceptions import \
    NoSuchElementException, ElementNotInteractableException, \
    TimeoutException, NoSuchShadowRootException, \
    StaleElementReferenceException, WebDriverException, UnexpectedAlertPresentException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.chrome.service import Service as ChromeDriverService
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# find_element_by_name('q') is replaced with find_element(By.NAME, 'q')
from selenium.webdriver.common.by import By

# https://stackoverflow.com/questions/36316465
# from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from selenium.webdriver.common.action_chains import ActionChains

from tpsup.nettools import is_tcp_open
import tpsup.pstools
import tpsup.tmptools
import os.path

from tpsup.utilbasic import hit_enter_to_continue
from tpsup.exectools import exec_into_globals

from typing import List, Union
from pprint import pformat
from tpsup.cmdtools import run_cmd_clean


# +----------+      +--------------+     +----------------+
# | selenium +----->+ chromedriver +---->+ chrome browser +---->internet
# +----------+      +--------------+     +----------------+

'''
########### start of global variables ###########
because we use a lot of eval(), therefore, we use many global variables.
note: global var is only global within the same module, ie, same file.

locator_driver is different from driver (aka. session)
when we enter a shadow, the shadow root is a new driver; we have to use
this new driver to run find_element_by_css. 
if we enter an iframe, even if it is a iframe within a shadow, we go
back to the original driver.
therefore, we use locator_driver to differentiate from original driver.
if driver's url changes, we reset the locator_driver to original driver.
therefore, we keep track of driver url too.

note: driver is the session, therefore it is global, no matter you make it a global var or not.
Making driver a global var signifies this fact.
Each shadowroot is also a global var. We use locator_driver to switch between shadowroot drivers.

I cannot find a way to save a copy of driver and then restore it later.

Class webdriver.Chrome and class ShadowRoot are parallel classes, not parent-child classes.
the class of locator_driver can be either webdriver.Chrome or ShadowRoot
    sitebase/python3/venv/Windows/win10-python3.12/Lib/site-packages/selenium/webdriver/remote/shadowroot.py
the class of driver is webdriver.Chrome
    sitebase/python3/venv/Windows/win10-python3.12/Lib/site-packages/selenium/webdriver/remote/webdriver.py
    sitebase/python3/venv/Windows/win10-python3.12/Lib/site-packages/selenium/webdriver/chrome/webdriver.py
therefore, we cast only driver, not locator_driver.
'''
driver: webdriver.Chrome = None
driver_url: str = None
locator_driver = None

# we use this to retrieve the effect after we eval code.
action_data = {}

# '1' return 1 layer, '2' return 2 layers, ....
# we start with 0, meaning we are outside of any layer, no layer to return
# everytime we break out a layer (while loop), we decrease return_levels by 1
return_levels = 0 

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

# last result from js code: jsr = driver.execute_script(js_code)
jsr = None

########### end of global variables ###########

class SeleniumEnv:
    def __init__(self, host_port: str = 'auto', **opt):
        # print(pformat(opt))
        # exit(1)
        global cmd
        self.host_port = host_port
        self.verbose = opt.get("verbose", 0)
        self.env = tpsup.envtools.Env()
        self.env.adapt()
        home_dir = os.path.normpath(
            self.env.home_dir)  # convert to native path

        # self.log_base = opt.get('log_base', home_dir)
        # because None could be passed down by __init__, we use two steps below
        self.log_base = opt.get('log_base', None)
        if self.log_base is None:
            self.log_base = home_dir
        system = self.env.system

        self.dryrun = opt.get("dryrun", False)
        self.driverlog = os.path.join(self.log_base, "selenium_driver.log")
        self.chromedir = os.path.join(self.log_base, "selenium_browser")
        # driver log on Windows must use Windows path, eg, C:/Users/tian/test.log.
        # Even when we run the script from Cygwin or GitBash, we still need to use Windows path.

        self.download_dir = tpsup.tmptools.tptmp(
            base=os.path.join(self.log_base, "Downloads", "selenium")
        ).get_nowdir(suffix="selenium", mkdir_now=False)  # no need to create it now

        self.headless = opt.get("headless", False)
        self.driver_exe = opt.get("driver", None)
        if self.driver_exe:
            if not which(self.driver_exe):
                raise RuntimeError(f"cannot find {self.driver_exe} in $PATH")
        else:
            self.driver_exe = check_setup().get('chromedriver')
            if not self.driver_exe:
                raise RuntimeError("cannot find chromedriver in PATH")

        # old hard-coded implementation
        # driver_path = f"{os.environ['SITEBASE']}/{self.env.system}/
        #                   {self.env.os_major}.{self.env.os_minor}/chromedriver"
        # driver_path = os.path.normpath(driver_path) # mainly for cygwin
        # os.environ["PATH"] = os.pathsep.join(
        #     [
        #         driver_path,
        #         # home_dir,    # we used to store the driver at home dir
        #         os.environ["PATH"],
        #     ]
        # )
        # we store chromedriver at $SITEBASE/(Linux|Windows)/major.minor/chromedriver/chromedriver.exe

        # if not re.search("[\\/]", self.driver_exe):
        #     # no path specified, then we are totally rely on $PATH
        #     driver_full_path = which(self.driver_exe)
        #     if driver_full_path is None:
        #         raise Exception(
        #             f'cannot find {self.driver_exe} in {os.environ["PATH"]}\n'
        #         )
        #     else:
        #         print(f"driver is {driver_full_path}")
        # else:
        #     # if path is specified, make sure it exist
        #     if not os.path.isfile(self.driver_exe):
        #         raise Exception(
        #             f"cannot find {self.driver_exe} not found. pwd={os.getcwd()}\n"
        #         )

        # chromedriver knows chrome.exe's path, therefore, normally we don't need to set it.
        # however, Windows keeps updating the system chrome.exe, making it incompatible with chromedriver,
        # which is downloaded manually.
        # the solution: save a copy of chrome somewhere, to keep chrome version static
        #    copy C:\Program Files (x86)\Google\Chrome to $USERPROFILE\Chrome
        # where
        #    $USERPROFILE is C:\users\userid

        # win_browser_path = None
        # if self.env.isWindows:
        #     static_browser_path = f"{os.environ['SITEBASE']}/{self.env.system}/'
        #       '{self.env.os_major}.{self.env.os_minor}/Chrome/Application/chrome.exe"
        #     static_browser_path = os.path.normpath(static_browser_path)
        #     # maily for cygwin/gitbash, to convert /cydrive/c/users/... to c:/users/...
        #
        #     if os.path.isfile(static_browser_path):
        #         print(f"we found browser at {static_browser_path}. we will use it")
        #         win_browser_path = static_browser_path
        #     else:
        #         print(f"browser is not found at {static_browser_path}. we will find it in PATH")

        self.driver_args = [
            "--verbose",
        ]  # for chromedriver

        if self.verbose:
            # print(sys.path)
            sys.stderr.write(f"SeleniumEnv.__init__: pwd={os.getcwd()}\n")
            sys.stderr.write(f'SeleniumEnv.__init__:PATH={os.environ["PATH"]}\n')

            self.print_running_drivers()

            if self.verbose > 1:
                if self.env.isLinux or self.env.isGitBash or self.env.isCygwin:
                    # display the beginning of the log file as 'tail' only display the later part
                    # use /dev/null to avoid error message in case the log file has not been created
                    cmd = f"cat /dev/null {self.driverlog}"
                    sys.stderr.write(f"cmd={cmd}\n")
                    os.system(cmd)

                    # --pid PID  exits when PID is gone
                    # -F         retry file if it doesn't exist
                    cmd = f"tail --pid {os.getpid()} -F -f {self.driverlog} &"
                    sys.stderr.write(f"SeleniumEnv.__init__: cmd={cmd}\n")
                    os.system(cmd)
                elif self.env.isWindows:
                    # windows doesn't have a way to do "tail -f file &"
                    # 1. from cmd.exe, we would have to call powershell to use "tail -f" equivalent, but will
                    #    have difficulty to make the process background.
                    # https://stackoverflow.com/questions/185575
                    # https://stackoverflow.com/questions/187587
                    # powershell.exe start-job -ScriptBlock \
                    #    { get-content C:/users/william/selenium_chromedriver.log -wait -tail 1 }
                    #
                    # 2. from powershell, Start-Job can easily run a ScriptBlock in background,
                    #    but the output will not come back to foreground.
                    # https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.core/start-job

                    # start-job -ScriptBlock \
                    #   { get-content C:/users/william/selenium_chromedriver.log -wait -tail 1 }
                    pass

        self.driver: webdriver.Chrome = None

        # https://www.selenium.dev/documentation/webdriver/drivers/options/
        # chrome_options will be used on chrome browser's command line not chromedriver's commandline
        self.browser_options = ChromeOptions()

        if host_port != "auto":
            # try to connect the browser in case already exists.
            # by setting this, we tell chromedriver not to start a browser
            self.browser_options.debugger_address = f"{host_port}"

            sys.stderr.write(f"SeleniumEnv.__init__: check browser port at {host_port}\n") 
            self.connected_existing_browser = False
            (host, port) = host_port.split(":", 1)
            if is_tcp_open(host, port):
                sys.stderr.write(
                    f"SeleniumEnv.__init__: {host_port} is open. let chromedriver to connect to it\n")
            else:
                raise RuntimeError(f"browser host_port={host_port} is not open.\n")

        if host_port == "auto":
            sys.stderr.write(
                "SeleniumEnv.__init__: chromedriver will auto start a browser and pick a port\n")

            if self.env.isLinux:
                # 2023/09/09,
                # 1. Linux chromedriver (116) had a bug with binary_location for Linux,
                #     default works.
                # 2. had to use "xhost +"
                # see tpsup/python3/examples/test_selenium_03_settings.py
                log_FileFuncLine(f"xhost +")
                run_cmd_clean("xhost +")
            else:
                self.browser_options.binary_location = get_browser_path()

            if self.headless:
                # self.browser_options.add_argument("--headless")

                # this is for chromedriver 129 only
                #   https://stackoverflow.com/questions/78996364
                #   we will remove it when we upgrade to chromedriver 130
                self.browser_options.add_argument("--headless --window-position=-2400,-2400")
                sys.stderr.write(" in headless mode\n")
        else:
            host, port = host_port.split(":", 1)
            self.browser_options.add_argument(
                f"--remote-debugging-port={port}")
            # self.browser_options.add_argument(f'--remote-debugging-address=127.0.0.1')

            if host.lower() != "localhost" and host != "127.0.0.1" and host != "":
                if self.dryrun:
                    sys.stderr.write(
                        "SeleniumEnv.__init__: cannot connect to remote browser, but this is dryrun, so we continue\n"
                    )
                else:
                    raise RuntimeError("cannot connect to remote browser.")
            else:
                sys.stderr.write(
                    "SeleniumEnv.__init__: cannot connect to an existing local browser. we will start up one.\n")
                self.browser_options.binary_location = get_browser_path()

                if self.headless:
                    self.browser_options.add_argument("--headless")
                    sys.stderr.write("SeleniumEnv.__init__: in headless mode\n")
                else:
                    sys.stderr.write("\n")

        if self.env.isLinux:
            self.browser_options.add_argument(
                "--no-sandbox")  # allow to run without root
            self.browser_options.add_argument(
                "--disable-dev_shm-usage")  # allow to run without root

        self.chromedir = self.chromedir.replace('\\', '/')

        self.browser_options.add_argument(f"--user-data-dir={self.chromedir}")

        # small window size can trigger mobile mode, sometimes causing complication
        # self.browser_options.add_argument("--window-size=960,540")

        # a bigger window size can reduce the mysterious timeouts. above 1000 should be good enough
        # so some even suggested to use maximized
        #    self.browser_options.add_argument("start-maximized")
        #    https://stackoverflow.com/a/26283818/1689770
        self.browser_options.add_argument("--window-size=1260,720")

        # 2022/8/25, got error
        #     Timed out receiving message from renderer:
        # https://stackoverflow.com/questions/48450594/selenium-timed-out-receiving-message-from-renderer
        # self.browser_options.add_argument("--window-size=1366,768");
        # self.browser_options.add_argument("--no-sandbox");
        self.browser_options.add_argument("--disable-gpu")
        self.browser_options.add_argument("--enable-javascript")
        self.browser_options.add_argument("disable-infobars")
        self.browser_options.add_argument("--disable-infobars")
        # self.browser_options.add_argument("--single-process");
        self.browser_options.add_argument("--disable-extensions")
        self.browser_options.add_argument("--disable-dev-shm-usage")
        # self.browser_options.add_argument("--headless");
        self.browser_options.add_argument("enable-automation")
        self.browser_options.add_argument("--disable-browser-side-navigation")
        # self.browser_options.add_experimental_option("excludeSwitches", ["enable-automation"])

        if opt.get("allowFile", 0):
            # this allow us to test with local files, ie, file:///. otherwise, you get 'origin' error
            # but this is security risk. so don't use it in production
            self.browser_options.add_argument("--allow-file-access-from-files")

        # enable console log
        # https://stackoverflow.com/questions/76430192
        # desired_capabilities has been replaced with set_capability
        self.browser_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

        for arg in opt.get("browserArgs", []):
            self.browser_options.add_argument(f"--{arg}")
            # chrome_options.add_argument('--proxy-pac-url=http://pac.abc.net')  # to run with proxy

        print(
            f"SeleniumEnv.__init__: browser_options.arguments = {pformat(self.browser_options.arguments)}")

        if self.dryrun:
            sys.stderr.write(
                "SeleniumEnv.__init__: this is dryrun, therefore, we don't start a webdriver, nor a browser\n"
            )
        else:
            # rotate the log file if it is bigger than the size.
            tpsup.logtools.rotate_log(
                self.driverlog, size=1024 * 1024 * 10, count=1)

            # make sure chromedriver is in the PATH
            # selenium 4.10+ need to wrap executable_path into Service
            # https://stackoverflow.com/questions/76428561
            driver_service = ChromeDriverService(
                # Service decides how driver starts and stops
                executable_path=self.driver_exe,
                log_path=self.driverlog,
                service_args=self.driver_args,  # for chromedriver
            )
            
            log_FileFuncLine()

            self.driver = webdriver.Chrome(
                service=driver_service,
                options=self.browser_options,
            )
            sys.stderr.write("SeleniumEnv.__init__: started\n")
            # if self.headless:
            #    time.sleep(1)  # throttle for the headless mode

            self.driver.driverEnv = self  # monkey patching for convenience

    def get_driver(self) -> webdriver.Chrome:
        return self.driver

    def delay_for_viewer(self, seconds: int = 1):
        if not self.headless:
            time.sleep(seconds)  # Let the user actually see something!

    def quit(self):
        if self.driver is not None:
            self.driver.close()
            self.driver.quit()
            self.driver = None

    def print_running_drivers(self):
        driver_basename = os.path.basename(self.driver_exe)
        tpsup.pstools.ps_grep(
            driver_basename, env=self.env, verbose=self.verbose
        )

    def get_attrs(self, element: WebElement, method: str = "bs4", verbose: int = 0):
        """
        get list of attributes from an element.
        https://stackoverflow.com/questions/27307131
        somehow, webdriver doesn't have an API for this
        :param element:
        :param method:
        :return:
        """
        """
        note: for html '<div class="login-greeting">Hi LCA Editor Tester,</div>'
        bs4 will give: {'class': ['login-greeting']}
        js  will give: {'class':  'login-greeting' }  
        """
        if method == "bs4":
            html: str = element.get_attribute("outerHTML")
            if verbose:
                tpsup.logtools.tplog(f"outerHTML={html}")
            if html:
                from bs4 import BeautifulSoup

                attrs = {}
                soup = BeautifulSoup(html, "html.parser")
                # https://www.crummy.com/software/BeautifulSoup/bs4/doc/#attributes
                for element in soup():
                    # soup() is a generator
                    # element.attrs is a dict
                    attrs.update(element.attrs)
                return attrs
            else:
                return {}
        elif method == "js":
            # java script. duplicate attributes will be overwritten
            js_script = (
                "var items = {}; "
                "for (index = 0; index < arguments[0].attributes.length; ++index) { "
                "   items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value"
                "};"
                "return items;"
            )
            attrs = self.driver.execute_script(js_script, element)
            return attrs
        else:
            raise RuntimeError(
                f"unsupported method={method}. accepted: bs4 or js")


def get_browser_path() -> str:
    path = check_setup().get('chrome')
    if not path:
        raise RuntimeError(f"cannot find chrome execuatble")
    return path


def print_js_console_log(**opt):
    global driver
    printed_header = 0
    for entry in driver.get_log('browser'):
        if not printed_header:
            print("------ begin console log -------")
            printed_header = 1
        # entry is a dict
        # entry = {
        #     'level': 'INFO',
        #     'message': 'console-api 7:8 "..."',
        #     'source': 'console-api',
        #     'timestamp': 1662997187656
        # }
        #
        print(entry['message'])
    if printed_header:
        print("------ end console log -------")


def get_driver(**args) -> webdriver.Chrome:
    # driverEnv = tpsup.seleniumtools.SeleniumEnv(**args)
    driverEnv = SeleniumEnv(**args)
    return driverEnv.get_driver()


def get_static_setup(**opt):
    verbose = opt.get('verbose', 0)

    env = tpsup.envtools.Env()
    env.adapt()
    static_setup = {}
    if env.isWindows:
        # as of now, only windows has static setup
        static_browser_path = f"{os.environ['SITEBASE']}/{env.system}/{env.os_major}.{env.os_minor}/Chrome/Application/chrome.exe"
        if verbose:
            print(f"get_static_setup: static_browser_path={static_browser_path}")

        if env.isWindows:
            # convert to native path: for windows, we convert it to batch path with forward slash for cygwin/gitbash/powershell
            static_browser_path = tpsup.envtools.convert_path(static_browser_path, target_type='batch')
            if verbose:
                print(f"get_static_setup: converted: static_browser_path={static_browser_path}")

        static_setup['chrome'] = static_browser_path

        static_driver_path = f"{os.environ['SITEBASE']}/{env.system}/{env.os_major}.{env.os_minor}/chromedriver/chromedriver.exe"
        print(f"get_static_setup: static_driver_path={static_driver_path}")

        if env.isWindows:
            # convert to native path: for windows, we convert it to batch path with forward slash for cygwin/gitbash/powershell
            static_driver_path = tpsup.envtools.convert_path(static_driver_path, target_type='batch')
            if verbose:
                print(f"get_static_setup: converted: static_driver_path={static_driver_path}")

        static_setup['chromedriver'] = static_driver_path

    return static_setup


def search_exec_in_path(execList: list, **opt) -> str:
    # search executable in PATH
    env = tpsup.envtools.Env()
    env.adapt()
    for exec in execList:
        exec_path = which(exec)
        if exec_path:
            return exec_path
    return None


def check_setup(**opt):
    target = opt.get('target')
    verbose = opt.get('verbose', 0)

    if target:
        targetList = [target]
    else:
        targetList = ['chrome', 'chromedriver']

    static_setup = get_static_setup(**opt)

    found_path = {}

    for exec in targetList:
        print("")

        path = None
        static_path = None
        if exec in static_setup:
            static_path = static_setup[exec]
            print(f"check_setup: static setup configured {exec}={static_path}")
            if os.path.isfile(static_path):
                path = static_setup[exec]
                print(f"check_setup: static setup's {exec}={static_path} exists.")
            else:
                print(f"check_setup: static setup's {exec}={static_path} doesn't exist.")

        if path:
            found_path[exec] = path
            continue

        if not static_path:
            print(f"static setup didn't configure {exec}.")
        if exec == 'chrome':
            # execList = ['google-chrome', 'chrome']
            execList = ['chrome']
        else:
            execList = [exec]

        path = search_exec_in_path(execList)
        if path:
            print(f"check_setup: found {exec}={path} in PATH")
            found_path[exec] = path
        else:
            print(f"check_setup: cannot find {exec} in PATH={os.environ['PATH']}")

    if opt.get('compareVersion', 0):
        print("")
        chrome_vesion = None
        chromedriver_vesion = None

        if found_path.get('chrome'):
            chrome_version_full_path = which('chrome_version')

            if not chrome_version_full_path:
                raise RuntimeError(
                    f"cannot find 'chrome_version' command in PATH={os.environ['PATH']}")

            print (f"check_setup: chrome_version_full_path={chrome_version_full_path}")
            print (f"check_setup: found_path['chrome']={found_path['chrome']}")

            cmd_term = tpsup.envtools.get_term_type()
            if cmd_term == 'batch':
                chrome_vesion = str(subprocess.check_output(
                    [chrome_version_full_path, found_path['chrome']]).strip(), 'utf-8')
                # 99.0.4844.74
            else:
                # convert backslash to forward slash
                found_path['chrome'] = found_path['chrome'].replace('\\', '/')
                print(f"check_setup: found_path['chrome']={found_path['chrome']}")
                chrome_vesion = run_cmd_clean(f"chrome_version {found_path['chrome']}", is_bash=True)
            # chrome_vesion = tpsup.cmdtools.run_cmd_clean(f"chrome_version {found_path['chrome'].replace('\\', '/')}", is_bash=True)

            # use str() to convert bytes to string

            print(f"check_setup: chrome version={chrome_vesion}")

            chrome_major = chrome_vesion.split('.')[0]

            print(f"check_setup: chrome major={chrome_major}")

        if found_path.get('chromedriver'):
            chromedriver_vesion = str(subprocess.check_output(
                [found_path['chromedriver'], '--version']).strip(), 'utf-8')
            # ChromeDriver 99.0.4844.51 (d537ec02474b5afe23684e7963d538896c63ac77-refs/branch-heads/4844@{#875})

            # use str() to convert bytes to string

            print(f"check_setup: chromedriver version={chromedriver_vesion}")

            chromedriver_vesion = chromedriver_vesion.split()[1]
            # 99.0.4844.74

            print(f"check_setup: chromedriver version={chromedriver_vesion}")

            chromedriver_major = chromedriver_vesion.split('.')[0]
            chromedriver_major = chromedriver_major

            print(f"check_setup: chromedriver version={chromedriver_vesion}")

        if chrome_vesion and chromedriver_vesion:
            if chrome_major != chromedriver_major:
                print(
                    f"check_setup: chrome major version {chrome_major} doesn't match chromedriver major version {chromedriver_major}")
                raise RuntimeError(
                    f"chrome major version {chrome_major} doesn't match chromedriver major version {chromedriver_major}")
            else:
                print(
                    f"check_setup: chrome major version {chrome_major} matches chromedriver major version {chromedriver_major}")
    return found_path


# https://stackoverflow.com/questions/47420957/create-custom-wait-until-condition-in-python

'''
Explicit Waits vs Implicit Waits
https://selenium-python.readthedocs.io/waits.html

WebDriverWait(driver, 10) is an example of explicit wait; it calls the the class defined below.
driver.find_element(By.XPATH, path) is an example of implicit wait; implicit wait is controlled by driver.implicitly_wait(10).
Therefore, in our code, we use explicit wait call to call a function that uses implicit wait.

Because explicit wait is the total wait time, which cover all iterations of implicit wait, 
we need to temporarily set implicit wait to 0 when we call WebDriverWait(driver, 10).until(...)
for below functions.
'''
class tp_find_element_by_paths:
    def __init__(self, type_paths: list, **opt):
        self.type_paths = type_paths
        self.opt = opt
        self.verbose = opt.get('verbose', 0)

    def __call__(self, driver):
        e = None
        i = 0
        for ptype, path in self.type_paths:
            if "xpath" in ptype:  # python's string.contains() method
                try:
                    e = driver.find_element(By.XPATH, path)
                except Exception:
                    i += 1
                    continue
            elif "css" in ptype:
                try:
                    e = driver.find_element(By.CSS_SELECTOR, path)
                except Exception:
                    i += 1
                    continue
            else:
                raise RuntimeError(f"unsupported path type={ptype}")

            # this is learned from perl
            #
            # auto-click or not ?!
            #    an element located by xpath is NOT the active (focused) element.
            #    we have to click it to make it active (foucsed)
            #
            #    on the other side, element located by tab is the active (focused)
            #    element
            #
            #    sounds like we should click on the element found by xpath.
            #    but then if it is submit button, clicking will trigger the action
            #    likely prematurally
            #
            # therefore, we introduced the click_xxxx switch
            if 'click_' in ptype:
                # click_xpath=//...
                # e.click()
                tp_click(e)

            print(f'tp_find_element_by_paths: found {ptype}="{path}"')

            # monkey-patch some self-identification info for convenience
            e.tpdata = {
                "ptype": ptype,
                "path": path,
                "position": i
            }
            break

        return e
    
    # defind an exit function


class tp_find_element_by_chains:
    # check whether one of the chains matches any element
    def __init__(self, chains: list, **opt):
        self.opt = opt
        self.verbose = opt.get('verbose', 0)
        self.matched_paths = []
        self.matched_numbers = []

        # this didn't work. error: IndexError: list assignment index out of range
        # i=0
        # for chain in chains:
        #     self.matched_paths[i] = []
        #     self.matched_numbers[i] = []
        #     i +=1

        self.chains = []
        for chain in chains:
            self.matched_paths.append([])
            self.matched_numbers.append([])
            self.chains.append([])

        # parse chains
        #
        #  example: convert ONE chain from
        #
        # [
        #     'xpath=/html/body[1]/ntp-app[1]', 'shadow', 'css=#mostVisited', 'shadow',
        #     '''
        #     css=#removeButton2,
        #     css=#actionMenuButton
        #     ''',
        # ],
        #
        # into
        #
        # [
        #     [['xpath', '/html/body[1]/ntp-app[1]']], [['shadow']] , [['css', '#mostVisited']], [['shadow']] ,
        #     [['css', '#removeButton2'], ['css', '#actionMenuButton']],
        # ]
        for i in range(0, len(chains)):
            chain = chains[i]
            for locator in chain:
                if (locator == "shadow") or (locator == "iframe"):
                    self.chains[i].append([[locator]])
                elif m1 := get_locator_compiled_path1().match(locator):
                    ptype, paths_string = m1.groups()
                    # default to strip blanks: space, tab, newline ...
                    paths_string = paths_string.strip()

                    type_paths = []
                    while m2 := get_locator_compiled_path2().match(paths_string):
                        path, type2 = m2.groups()
                        end_pos = m2.end()

                        # rstrip():  right (rear) strip();
                        # lstrip: left (leading) strip;
                        # strip(): both.
                        # default to strip blanks: space, tab, newline ...
                        # here we also strip the ending comma.
                        # todo: find a better way to strip ending space and comma
                        # print(f'path1={pformat(path)}')
                        path = path.rstrip().rstrip(",").rstrip()
                        # print(f'path2={pformat(path)}')

                        type_paths.append([ptype, path])
                        ptype = type2  # to be used in next round
                        paths_string = paths_string[end_pos:]

                    path = paths_string  # leftover is a path
                    # todo: find a better way to strip endinng space and comma
                    # print(f'path1={pformat(path)}')
                    path = path.rstrip().rstrip(",").rstrip()
                    # print(f'path2={pformat(path)}')

                    type_paths.append([ptype, path])
                    self.chains[i].append(type_paths)
                else:
                    raise RuntimeError(f"unsupported 'locator={locator}'")

    def __call__(self, driver):
        e: WebElement = None

        if self.verbose:
            print(f'parsed chains = {pformat(self.chains)}')

        for i in range(0, len(self.chains)):
            chain = self.chains[i]
            if self.verbose:
                print(f'testing chain = {pformat(chain)}')

            locator_driver = driver
            self.matched_numbers[i].clear()
            self.matched_paths[i].clear()

            found_chain = True

            for locator in chain:
                if self.verbose:
                    print(f'testing locator = {pformat(locator)}')
                if locator[0][0] == "shadow":
                    try:
                        locator_driver = e.shadow_root  # shadow_driver is a webdriver type
                        self.matched_numbers[i].append("0")
                        self.matched_paths[i].append(locator[0][0])
                        if self.verbose:
                            print(f"found {locator[0][0]}")
                    except Exception as ex:
                        if self.verbose:
                            print(f"not found {locator[0][0]}")
                        found_chain = False
                        break
                elif locator[0][0] == "iframe":
                    try:
                        # https://www.selenium.dev/selenium/docs/api/py/webdriver_remote/selenium.webdriver.remote.switch_to.html#selenium.webdriver.remote.switch_to.SwitchTo.frame
                        driver.switch_to.frame(e)
                        locator_driver = driver
                        self.matched_numbers[i].append("0")
                        self.matched_paths[i].append(locator[0][0])
                        if self.verbose:
                            print(f"found {locator[0][0]}")
                    except Exception as ex:
                        if self.verbose:
                            print(f"not found {locator[0][0]}")
                        found_chain = False
                        break
                else:
                    type_paths = locator
                    if self.verbose:
                        print(f"paths = {pformat(type_paths)}")

                    one_parallel_path_matched = False
                    j = 0
                    for ptype, path in type_paths:
                        if self.verbose:
                            print(f'testing {ptype}={path}')
                        if "xpath" in ptype:  # python's string.contains() method
                            try:
                                e = locator_driver.find_element(By.XPATH, path)
                            except Exception:
                                j += 1
                                continue
                        elif "css" in ptype:
                            try:
                                e = locator_driver.find_element(
                                    By.CSS_SELECTOR, path)
                            except Exception:
                                j += 1
                                continue
                        else:
                            raise RuntimeError(
                                f"unsupported path type={ptype}")

                        self.matched_numbers[i].append(f"{j}")
                        self.matched_paths[i].append(f"{ptype}={path}")
                        if self.verbose:
                            print(f'found {ptype}="{path}"')
                        one_parallel_path_matched = True
                        break
                    if self.verbose:
                        print(
                            f'one_parallel_path_matched={pformat(one_parallel_path_matched)}')
                    if not one_parallel_path_matched:
                        found_chain = False
                        break

                if not e:
                    # some locators don't explicitly return an element, therefore, we set it here.
                    e = driver.switch_to.active_element
                    if not e:
                        raise RuntimeError(f'cannot find active element')
                self.current_matched_path = self.matched_paths[i].copy

            if found_chain:
                # e.tpdata = {"ptype" : ptype, "path" : path, "position" : i}

                e.tpdata = {
                    "matched_chain": self.matched_paths[i].copy(),
                    "position": f"{i}." + ".".join(self.matched_numbers[i])
                }  # monkey patch for convenience

                return e
        return None


def tp_get_url(url: str, **opt):
    global driver
    # driver.get(url) often got the following error:
    #   selenium.common.exceptions.TimeoutException:
    #   Message: timeout: Timed out receiving message from renderer: 10.243
    #
    # https://stackoverflow.com/questions/40514022/chrome-webdriver-produces-timeout-in-selenium
    try:
        driver.get(url)
    except TimeoutException as ex:
        # driver.get(url) often got the following error:
        #   selenium.common.exceptions.TimeoutException:
        #   Message: timeout: Timed out receiving message from renderer: 10.243
        #
        # https://stackoverflow.com/questions/40514022/chrome-webdriver-produces-timeout-in-selenium
        print(ex.msg)
        print(f"\nseen 'TimeoutException receiving message from renderer' again? do driver.refresh(). If this doesn't help, then set pagewait (page_load_timeout) longer.\n")
        driver.refresh()
        # if the above doesn't work, then we need to make page_load_timeout longer.
    except WebDriverException as ex:
        # selenium.common.exceptions.WebDriverException: Message: target frame detached
        # if see the above error, try again
        print(ex.msg)
        print(f"\nseen 'WebDriverException Message: target frame detached' again? try the url again.\n")
        driver.get(url)
    if opt.get('accept_alert', 0):
        time.sleep(1)  # sleep 1 second to let alert to show up
        if opt.get('interactive'):
            print("expect alert to show up")
            hit_enter_to_continue()

        # https://stackoverflow.com/questions/19003003/check-if-any-alert-exists-using-selenium-with-python
        try:
            WebDriverWait(driver, wait_seconds).until(EC.alert_is_present(),
                                           'Timed out waiting for PA creation ' +
                                           'confirmation popup to appear.')

            alert = driver.switch_to.alert
            alert.accept()
            print("alert accepted")
        except TimeoutException:
            print("no alert")


# we will use the following patterns more than once, therefore,
# we centralize them into functions, so we can easily change their behavior
def get_locator_compiled_path1():
    return re.compile(r"\s*(xpath|css|click_xpath|click_css)=(.+)",
                      re.MULTILINE | re.DOTALL)


def get_locator_compiled_path2():
    return re.compile(
        r"(.+?)(?:\n|\r\n|\s?)*,(?:\n|\r\n|\s?)*(xpath|css|click_xpath|click_css)=",
        re.MULTILINE | re.DOTALL)

dump_readme = '''
element/
    directory for element dump

dom/
    directory for dom dump

page/
    directory for page dump

iframe*.html
    the iframe html of the page (dump all) or specified element (dump element)
    note that when there is a shadow dom, the iframe*.html doesn't show the shadow dom;
    you need to look at shadow*.html for that.

locator_chain_list.txt
    the locator chain on command line format
    eg
        "xpath=id('shadow_host')" "shadow"
        "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow"

locator_chain_map.txt
    The most useful file!!!

    the locator chain to shadow/iframe mapping. this shows how to reach to 
    each shadow or iframe from the root or the specified element.
    you can run ptslnm_locate with the chain on command line to locate the element.
    eg
        iframe001: "xpath=/html[1]/body[1]/iframe[1]" "iframe"
        iframe001.shadow001: "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')" "shadow"
        iframe001.shadow001.shadow002: "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow"
    
    you may see shadow doms not defined by you. for example, form input may have a shadow dom.
        <!-- shadow_test2_main.html -->
        <input type="checkbox" />
        <input type="file" />
    they create two shadow doms
        shadow001.shadow003: "xpath=id('shadow_host')" "shadow" "css=INPUT:nth-child(4)" "shadow"
        shadow001.shadow004: "xpath=id('shadow_host')" "shadow" "css=INPUT:nth-child(6)" "shadow"

screenshot_element.png
    the screenshot of the element
    as of 2024/12/15, it works in -js mode. non-js mode screenshot is blank.

shadow*.html
    the shadow dom of the page or specific element.
    it is the HTML of the shadow host.

source.html
    the source html specific to dump scope: element, or dom, or the whoe page: 
        if dump_element, this will be the html of the element.
        if dump_dom, this will be the html of the innest iframe dom that contains the element.
                     we cannot get the innest shadow dom html because shadowRoot (shadow driver) 
                     has no page_source attribute.
        if dump_all, this will be the whole page.

    dump_element and dump_dom are reliable because they are not affected by the driver's state (in iframe/shadow or not).
    dump_page is unreliable or have side effect because it needs to switch driver to the original driver.

    note that when there is a shadow dom, the source.html doesn't show the shadow dom's full content.
    you need to look at shadow*.html for that.

    normally source.html will be different from the original html because source.html contains
    dynamic content, such as the content of shadow dom or js generated content.

    you will see see some tags are neither from the original html nor from the js that you provided.
    for example: 
        <input type="button" value="Choose File" pseudo="-webkit-file-upload-button" id="file-upload-button" aria-hidden="true">
    here,
        'aria' (Accessible Rich Internet Applications) is a set attributes that define ways to make web content and web 
        applications (especially those developed with JavaScript) more accessible to people with disabilities.

        'pseudo': A CSS pseudo-class is a keyword added to a selector that specifies a special state of the selected element(s).
        For example, the pseudo-class :hover can be used to select a button when a user's pointer hovers over the button and
        this selected button can then be styled.

xpath_chain_list.txt
    similar to locator_chain_list.txt, but only xpath
    eg
        /html[1]/body[1]/iframe[1] iframe
        /html[1]/body[1]/iframe[1] iframe id('shadow_host') shadow
        /html[1]/body[1]/iframe[1] iframe id('shadow_host') shadow /div[@id='nested_shadow_host'] shadow
    note: xpath* files are less useful than locator* files, because xpath is not useable in shadow dom.

xpath_chain_map.txt
    similar to locator_chain_map.txt, but only xpath
    eg
        iframe001: /html[1]/body[1]/iframe[1] iframe
        iframe001.shadow001: /html[1]/body[1]/iframe[1] iframe id('shadow_host') shadow
        iframe001.shadow001.shadow002: /html[1]/body[1]/iframe[1] iframe id('shadow_host') shadow /div[@id='nested_shadow_host'] shadow
    note: xpath* files are less useful than locator* files, because xpath is not useable in shadow dom.

xpath_list.txt
    all xpaths of shadow/iframe.
    The list are single x-paths pointing to iframe/shadow, not a chain as in xpath_chain_list.txt
    eg
        /html[1]/body[1]/iframe[1]
        id('shadow_host')
        /iframe[1]
        /div[@id='nested_shadow_host']
    note: xpath* files are less useful than locator* files, because xpath is not useable in shadow dom.

xpath_map.txt
    map between xpath and shadow/iframe. 
    This map uses a single xpath to locate a iframe/shadow, not a chain as in xpath_chain_map.txt
    eg
        iframe001: /html[1]/body[1]/iframe[1]
        shadow001: id('shadow_host')
        shadow001.iframe002: /iframe[1]
        shadow001.shadow002: /div[@id='nested_shadow_host']
    note: xpath* files are less useful than locator* files, because xpath is not useable in shadow dom.
    for example, the last line above is a nested shadow dom, which is not reachable by the xpath.

How to use these files:
    scenario 1: I want to locate the search box in google new tab page
        dump the page
            $ ptslnm -rm newtab -dump $HOME/dumpdir -scope all
        open browser, go to new tab page, open devtools, inspect the search box html
            it has: id="input"
        find this string in our dump files
            $ cd $HOME/dumpdir/page
            $ grep 'id="input"' *
            shadow009.html:<div id="inputWrapper"><input id="input" class="truncate" type="search" ...
            shadow028.html:        <input id="input" part="input" autocomplete="off" ...

            shadow009.html is the shadow dom that contains the search box.

            find the locator chain for shadow009.html
            $ grep shadow009 locator_chain_map.txt
            shadow006.shadow009: "xpath=/html[@class='focus-outline-visible']/body[1]/ntp-app[1]" "shadow" "css=#searchbox" "shadow"

            this locator chain will bring us the the shadow that contains the search box.
        now we need to find the css selector (xpath doesn't work in shadow dom) for the search box
            in browser, inspect the search box. in devtools, right click the search box, copy css selector.
            it is: #searchbox

        now we can locate the search box
            $ ptslnm_locate newtab -locator "xpath=/html[@class='focus-outline-visible']/body[1]/ntp-app[1]" "shadow" "css=#searchbox"
    
'''

def dump(output_dir: str, element: WebElement = None, **opt):
    global driver
    verbose = opt.get('verbose', 0)
    debug = opt.get('debug', 0)

    os.makedirs(output_dir, exist_ok=True)  # this is mkdir -p
    
    if element:
        # this part takes care of dump_scope=element
        source_file = f"{output_dir}/source_element.html"
        with open(source_file, "w", encoding="utf-8") as source_fh:
            source_fh.write(element.get_attribute('outerHTML'))
            # screenshot the element
            # element.click()

        element.screenshot(f"{output_dir}/screenshot_element.png")

        # dump shadow host if any. note: we cannot dump shadowRoot.
        source_file = f"{output_dir}/source_shadowhost.html"
        # shadowHost = js_get_shadowhost(element)
        shadowHost = js_get(element, "shadowHost")
        if shadowHost:
            with open(source_file, "w", encoding="utf-8") as source_fh:
                source_fh.write(shadowHost.get_attribute('outerHTML'))
    else:
        # this part takes care of dump_scope=dom or dump_scope=page
        source_file = f"{output_dir}/source.html"
        with open(source_file, "w", encoding="utf-8") as source_fh:  
            '''
            driver.page_source may not be the whole page.
                - If driver is in iframe, driver.page_source will only show
                  the content of the iframe. (dump_scope=iframe)
                - if driver is not in any iframe, driver.page_source will show
                  the whole page. (dump_scope=page)
                - if driver enters shadowRoot, shadowRoot doesn't have page_source,
                  therefore, we can only use driver.pagesource to get the shadow's
                  parent iframe's source.
            but driver.page_source will not show the content of the iframe or shadow inside it.
            If we are in an iframe and wanted to see the whole page, we need to go out of iframe
            using driver.switch_to.default_content()
            '''
            source_fh.write(driver.page_source)
           
            # locator_dirver.page_source doesn't work, error:
            #    AttributeError: 'ShadowRoot' object has no attribute 'page_source'
            # source_fh.write(locator_driver.page_source)
        source_fh.close()

    if element is None:
        iframe_list = driver.find_elements(By.XPATH, '//iframe')
        # driverwait = WebDriverWait(driver, 20)
        # iframe_list = driverwait.until(EC.presence_of_all_elements_located((By.XPATH, '//iframe')))
    else:
        iframe_list = element.find_elements(By.XPATH, './/iframe')

    dump_state = {
        'output_dir': output_dir,
        'type_chain': [],  # iframe, shadow
        'typekey_chain': [],  # iframe001, shadow001
        'locator_chain': [],  # 'xpath=/a/b', 'shadow', 'css=div'
        'xpath_chain': [],  # /a/b, shadow, /div
        'scan_count': {
            'iframe': 0,
            'shadow': 0,
        },
        'exist_count': {
            'iframe': 0,
            'shadow': 0,
        },
        'max_depth_so_far': 0,
    }

    for format in ['list', 'map']:
        dump_state[format] = {}
        for scheme in ['locator_chain', 'xpath_chain', 'xpath']:
            f = f"{output_dir}/{scheme}_{format}.txt"
            dump_state[format][scheme] = open(f, "w", encoding="utf-8")

    for iframe in iframe_list:
        dump_deeper(iframe, dump_state, 'iframe', **opt)

    # get all shadow doms
    #
    # https://developer.mozilla.org/en-US/docs/Web/Web_Components/Using_shadow_DOM
    #   There are some bits of shadow DOM terminology to be aware of:
    #     Shadow host: The regular DOM node that the shadow DOM is attached to.
    #     Shadow tree: The DOM tree inside the shadow DOM.
    #     Shadow boundary: the place where the shadow DOM ends, and the regular DOM begins.
    #     Shadow root: The root node of the shadow tree.
    #

    start_node: webdriver.Chrome = None
    find_path: str = None
    if element is None:
        start_node = driver
        find_path = '//*'
    else:
        start_node = element
        find_path = './/*'
        dump_deeper(element, dump_state, 'shadow',
                    **opt)  # don't forget element itself

    for e in start_node.find_elements(By.XPATH, find_path):
        dump_deeper(e, dump_state, 'shadow', **opt)

    for format in ['list', 'map']:
        for scheme in ['xpath', 'xpath_chain', 'locator_chain']:
            dump_state[format][scheme].close()

    # summary and final stats
    print(f"\nfinal dump_state = {pformat(dump_state)}")
    iframe_scan_count = dump_state['scan_count']['iframe']
    shadow_scan_count = dump_state['scan_count']['shadow']
    total_scan_count = iframe_scan_count + shadow_scan_count
    scan_depth = len(dump_state['type_chain'])
    max_depth_so_far = dump_state['max_depth_so_far']
    print(f"total scanned {total_scan_count}, for iframe {iframe_scan_count}, "
          f"for shadow {shadow_scan_count}. iframe can be scanned by locator, therefore, less count.")
    print(
        f"current depth={scan_depth}, max depth so far={max_depth_so_far}, max_exist_depth is 1 less")

    # we put the chain check at last so that we won't miss the summary
    if scan_depth != 0:
        raise RuntimeError(f"dump_state type_chain is not empty")


def dump_deeper(element: WebElement, dump_state: dict, type: str, **opt):
    verbose = opt.get('verbose', 0)

    dump_state['scan_count'][type] += 1
    iframe_scan_count = dump_state['scan_count']['iframe']
    shadow_scan_count = dump_state['scan_count']['shadow']
    total_scan_count = iframe_scan_count + shadow_scan_count
    scan_depth = len(dump_state['type_chain'])
    if scan_depth > dump_state['max_depth_so_far']:
        dump_state['max_depth_so_far'] = scan_depth

    max_depth_so_far = dump_state['max_depth_so_far']

    limit_depth = opt.get('limit_depth', 5)

    if ((total_scan_count % 100) == 0) or (scan_depth >= limit_depth):
        print(
            f"total scanned {total_scan_count}, for iframe {iframe_scan_count}, for shadow {shadow_scan_count}")
        print(
            f"current depth={scan_depth}, max depth so far={max_depth_so_far}, max_exist_depth is 1 less")
        if scan_depth >= limit_depth:
            # raise RuntimeError(f"current depth={scan_depth} > limit_depth={limit_depth}")
            print(
                f"current depth={scan_depth} >= limit_depth={limit_depth}, we stop going deeper, going back")
            return

    if type == 'shadow':
        try:
            if element.shadow_root:
                pass
        except NoSuchShadowRootException:
            if verbose > 1:
                xpath = js_get(element, 'xpath', **opt)
                print(f'no shadow root under xpath={xpath}')
            return

    print(f"dump_state = {pformat(dump_state)}")
    print(f"type = {type}")

    # selenium.common.exceptions.StaleElementReferenceException: Message: stale element reference:
    #   element is not attached to the page document
    xpath: str = None
    css: str = None

    try:
        xpath = js_get(element, 'xpath', **opt)
    except StaleElementReferenceException as e:
        print(e)
        print(f"we skipped this {type}")
        return

    shadowed = False
    if 'shadow' in dump_state['type_chain']:
        shadowed = True

    if shadowed:
        # shadow root only support css, not xpath
        try:
            css = js_get(element, 'css', **opt)
        except StaleElementReferenceException as e:
            print(e)
            print(f"we skipped this {type}")
            return

    output_dir = dump_state['output_dir']

    dump_state['exist_count'][type] += 1
    i = dump_state['exist_count'][type]

    typekey = f'{type}{i:03d}'  # padding
    dump_state['type_chain'].append(type)
    dump_state['typekey_chain'].append(typekey)
    dump_state['xpath_chain'].extend([xpath, type])
    if shadowed:
        dump_state['locator_chain'].extend([f"css={css}", type])
    else:
        dump_state['locator_chain'].extend([f"xpath={xpath}", type])
    output_file = f"{output_dir}/{typekey}.html"

    typekey_chain = '.'.join(dump_state['typekey_chain'])
    line = f"{typekey_chain}: {xpath}"
    print(line)
    dump_state['map']['xpath'].write(line + "\n")
    dump_state['list']['xpath'].write(xpath + "\n")

    xpath_chain = ' '.join(dump_state['xpath_chain'])
    line = f'{typekey_chain}: {xpath_chain}'
    dump_state['map']['xpath_chain'].write(line + "\n")
    dump_state['list']['xpath_chain'].write(xpath_chain + "\n")

    locator_chain = '"' + '" "'.join(dump_state['locator_chain']) + '"'
    line = f'{typekey_chain}: {locator_chain}'
    dump_state['map']['locator_chain'].write(line + "\n")
    dump_state['list']['locator_chain'].write(locator_chain + "\n")

    if type == 'iframe':
        # https://www.selenium.dev/selenium/docs/api/py/webdriver_remote/selenium.webdriver.remote.switch_to.html#selenium.webdriver.remote.switch_to.SwitchTo.frame
        driver.switch_to.frame(element)
        # tp_switch_to_frame(element)
        with open(output_file, "w", encoding="utf-8") as ofh:
            ofh.write(driver.page_source)
            ofh.close()

        # find sub iframes in this frame
        iframe_list = driver.find_elements(By.XPATH, '//iframe')
        for sub_frame in iframe_list:
            dump_deeper(sub_frame, dump_state, 'iframe', **opt)

        # find shadows in this frame
        for e in driver.find_elements(By.XPATH, "//*"):
            dump_deeper(e, dump_state, 'shadow', **opt)

        # don't forget to switch back to main web page.
        # driver.switch_to.default_content()
        tp_switch_to_top()

        # DON'T switch back to the last iframe, because we will switch back in the caller, locate().
        # If we do it here, then the caller's switch_to.frame(last_iframe) will fail with error:
        #     element is not found.
        # if last_iframe:
        #     driver.switch_to.frame(last_iframe)

        #     print("driver.switch_to.frame(last_iframe) worked. hit enter to continue")
        #     hit_enter_to_continue()
 
    elif type == 'shadow':
        # shadow_host = element
        shadow_driver = element.shadow_root
        # shadow_host.shadow_root is a webdriver
        # https://titusfortner.com/2021/11/22/shadow-dom-selenium.html
        #    What happened in v96 is that Chromium has made its shadow root values compliant
        #    with the updated W3C WebDriver specification, which now includes definitions
        #    getting an element’s shadow root and locating elements in a shadow root.
        #
        #    Selenium 4 with Chromium 96 provides a much cleaner API for working with Shadow
        #    DOM elements without needing to use JavaScript.
        #
        # print(f"{pformat(shadow_driver)}")
        # <selenium.webdriver.remote.shadowroot.ShadowRoot (session="6092d3d82416d06d0e7bb0af0119ecb9",
        # element="cc68958a-cd37-4b71-bb71-f71d9480537a")>

        # print(f"{pformat(shadow_driver.__getattribute__('element'))}")
        # AttributeError: 'ShadowRoot' object has no attribute 'element'

        # as of 2022/09/04, shadow root only support CSS SELECTOR
        # I need to get the html of the shadow root

        # XPATH is not a supported locator for shadow root
        # shadow_root:WebElement = shadow_driver.find_element(By.XPATH, '/')

        # :root and :host don't work for shadow root. There is no root element to shadow root
        # shadow_root:WebElement = shadow_driver.find_element(By.CSS_SELECTOR, ':root')
        # shadow_root:WebElement = shadow_driver.find_element(By.CSS_SELECTOR, ':host')

        # Instead, we should just go through all top-level nodes under shadow root, ':host > *'
        # https://stackoverflow.com/questions/42627939

        ofh = open(output_file, "w", encoding="utf-8")

        for e in shadow_driver.find_elements(By.CSS_SELECTOR, ':host > *'):
            ofh.write(e.get_attribute('outerHTML'))
            ofh.write("\n")
        ofh.close()

        # find sub iframes in this shadow
        iframe_list = shadow_driver.find_elements(By.CSS_SELECTOR, 'iframe')
        for iframe in iframe_list:
            dump_deeper(iframe, dump_state, 'iframe', **opt)

        # find child shadows in this shadow, can only use CSS SELECTOR
        # https://stackoverflow.com/questions/42627939
        for e in shadow_driver.find_elements(By.CSS_SELECTOR, '*'):
            # 2022/09/16, this python script got more elements than my perl script.
            # I used the internal id, element.id, to detect dups. no dups found.
            # turned out that perl and python scripts used different data dir. the extra
            # elements python found was the cached site urls.
            #
            # seen = {} # python set internally is like dict. therefore, we use dict as set
            # if e.id in seen:
            #     seen[e.id] += 1
            #     raise RuntimeError(f'seeing dup element id={e.id}')
            #     # continue
            # else:
            #     seen[e.id] = 1
            dump_deeper(e, dump_state, 'shadow', **opt)

    poptype = dump_state['type_chain'].pop()
    popkey = dump_state['typekey_chain'].pop()
    if popkey != typekey:
        raise RuntimeError(
            f"pop_key={popkey} is not the same expected type_key={typekey}")

    pop_xpath_chain1 = dump_state['xpath_chain'].pop()
    pop_xpath_chain2 = dump_state['xpath_chain'].pop()
    pop_locator_chain1 = dump_state['locator_chain'].pop()
    pop_locator_chain2 = dump_state['locator_chain'].pop()

def locator_chain_to_js_list(locator_chain: list, **opt) -> list:
    '''
    the conversion is not 1 to 1, meaning there are likely less number
    of items in js_list the in locator_chain
    '''
    js_list: list = []
    trap = opt.get('trap', 0)
    debug = opt.get('debug', 0)

    '''
    window vs screen vs and document
        https://stackoverflow.com/questions/9895202
    
        - window is the main JavaScript object root, aka the global object in a browser, and it can
          also be treated as the root of the document object model. You can access it as window.

        - window.screen or just screen is a small information object about physical screen dimensions.

        - window.document or just document is the main object of the potentially visible (or better
          yet: rendered) document object model/DOM.

        - viewport is the rectangle of the rendered document seen within the tab or frame

    Since window is the global object, you can reference any properties of it with just the property
    name - so you do not have to write down window. - it will be figured out by the runtime.
    therefore window.document is the same as document.

    let vs var vs const
        - "let" allows you to declare variables that are limited to the scope of a block ({}).
          for example, "if" block, "for" block, or "while" block. 
          note: python's "if" doesn't limit the scope of variables.
        - "var" is function scoped when it is declared within a function.
          if it is declared outside a function, it is global.
        - "const" is block scoped, like "let". 
    '''

    in_shadowDom = False

    js = 'var e = document'
    for locator in locator_chain:
        if m := get_locator_compiled_path1().match(locator):
            # we can only convert single path, eg, xpath=/a/b
            # we cannot conver multiple path, eg, xpath=/a/b,xpath=/c/d
            ptype, path = m.groups()
            if ptype == 'xpath':
                if not in_shadowDom:
                    js += f'.evaluate("{path}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue'
                else:
                    raise RuntimeError("xpath is not supported in shadow dom. use css instead")
            elif ptype == 'css':
                js += f'.querySelector("{path}")'
            else:
                raise RuntimeError(
                    f"unsupported ptype={ptype} in locator={locator}")
        elif locator == 'shadow':
            js += '.shadowRoot' # this is the shadow driver
            in_shadowDom = True    
        elif locator == 'iframe':
            """
            https://stackoverflow.com/questions/7961229/

            cd(iframe_element) only works in Firefox
            js += '.contentWindow;\ncd(element);\nelement = document'
                        js += ''';
            const current_origin = window.location.origin;
            
            var iframe_src = e.getAttribute('src');
            // alert(`iframe_src=${iframe_src}`);
            var iframe_url = null
            var iframe_origin = null
            if (iframe_src) {
                //https://developer.mozilla.org/en-US/docs/Web/API/URL/origin
                iframe_url = new URL(iframe_src);
                // console.log(`iframe_url=${iframe_url}`);
                alert(`iframe_url=${iframe_url}`);
                iframe_origin = iframe_url.origin;
            }
            
            var iframe_inner = null;
            if ( (!iframe_origin) || (current_origin.toUpperCase() === iframe_origin.toUpperCase()) ) {
                //case-insensitive compare
                console.log(`iframe stays in the same origin ${current_origin}`); // note to use backticks
                iframe_inner=e.contentDocument || e.contentWindow.document;
                document = iframe_inner
            } else {
                console.log(`iframe needs new url ${iframe_url}`);  // note to use backticks
                window.location.replace(iframe_url);
            }
                '''

            problem: when work with local file, ie, file:///... , we got origin issue. Error is like
                SecurityError: Failed to read a named property 'document' from 'Window':
                    : Blocked a frame with origin \"null\" from accessing a cross-origin frame.
            solution: 
                for production: use a web server to serve the file.
                for testing: use --allow-file-access-from-files for the browser. this is security risk.
            """
            js += '''
try {
    let iframe_inner = e.contentDocument || e.contentWindow.document;
    document = iframe_inner
    const current_origin = window.location.origin;
    console.log(`iframe stays in the same origin ${current_origin}`); // note to use backticks
} catch(err) {
    // print the error. note that console.log() is not available in Selenium. 
    // console log is only available in browser's webtools console.
    // we have a locator 'consolelog' to print it out. 
    console.log(err.stack);

    let iframe_src = e.getAttribute('src');
    //iframe_url = new URL(iframe_src);
    iframe_url = iframe_src;
    console.log(`iframe needs new url ${iframe_url}`);  // note to use backticks
    window.location.replace(iframe_url);
}
            '''
            # save one js after very iframe.
            # so every 'iframe' creates a new js. 
            if trap:
                js = wrap_js_in_trap(js)
            js_list.append(js)

            # start another js
            js = 'var e = document'

            # once we are in iframe, we are out of shadow driver, back to normal driver.
            # even if the iframe is in shadow dom.
            in_shadowDom = False
        else:
            raise RuntimeError(f"unsupported locator={locator}. js only accept locators: xpath, css, shadow, or iframe")
  
    '''
    this is the last js.
    if the last js ends with a shadowRoot, we remove it because
    we shadowRoot (shadow driver) doesn't support a lot of methods.
    for example, we cannot run dump() on shadowRoot
        source_fh.write(element.get_attribute('outerHTML'))
                    ^^^^^^^^^^^^^^^^^^^^^
        AttributeError: 'ShadowRoot' object has no attribute 'get_attribute'. Did you mean: '__getattribute__'?
    we can run dump() on shadow host.
    But we need shadowRoot to run querySelector() to locate element in shadow dom. (see comment on 
    'locator_dirver' vs 'driver'). Therefore,
        if ShadowRoot is the last js, we remove it.
        if ShadowRoot is followed by querySelector(), we keep it.
    '''
    if js.endswith('.shadowRoot'):
        js = js[:-len('.shadowRoot')]

    # save the last js.
    #   - only the last js 'return e'
    #   - the intermediate js were all ending with iframes
    js += ';\nreturn e'
    if trap:
        js = wrap_js_in_trap(js)

    js_list.append(js)

    if debug:
        print(f"locator_chain_to_js_list: js_list_size={len(js_list)}")
        i = 0
        for item in js_list:
            print(f"js{i}={item}")
            print(f"")
            i += 1

    return js_list

def locator_chain_to_locator_chain_using_js(locator_chain: list, **opt) -> list:
    # because only xpath/css/iframe/shadow in a locator chain can be converted to js, we often
    # cannot convert the whole locator chain to js. Therefore, we only convert the first part
    # of xpath/css/iframe/shadow chain to js, and leave the rest as is.
    # for example, if the locator_chain is
    #    sleep=2 xpath=/a/b shadow css=c comment=done css=d
    # we will convert "xpath=/a/b shadow css=c" to js, and leave the rest as is.

    debug = opt.get('debug', 0)
    
    locator_chain_before_js = []
    locator_chain_after_js = []
    
    # first we find the first part of locator_chain that can be converted to js
    to_be_converted = []
    to_be_converted_started = False
    to_be_converted_ended = False
    for locator in locator_chain:
        if to_be_converted_ended:
            locator_chain_after_js.append(locator)
            continue

        if not to_be_converted_started:
            if re.match(r"\s*(xpath|css|iframe|shadow)", locator):
                to_be_converted.append(locator)
                to_be_converted_started = True
            else:
                locator_chain_before_js.append(locator)
            continue

        if to_be_converted_started:
            if re.match(r"\s*(xpath|css|iframe|shadow)", locator):
                to_be_converted.append(locator)
            else:
                to_be_converted_ended = True
                locator_chain_after_js.append(locator)

    if debug:
        print(f"locator_chain_before_js={pformat(locator_chain_before_js)}")
        print(f"to_be_converted={pformat(to_be_converted)}")
        print(f"locator_chain_after_js={pformat(locator_chain_after_js)}")

    locator_chain2 = locator_chain_before_js.copy()

    if to_be_converted:
        js_list = locator_chain_to_js_list(to_be_converted, **opt)
        js_locator_chain = js_list_to_locator_chain(js_list, **opt)
        locator_chain2.extend(js_locator_chain)

    locator_chain2.extend(locator_chain_after_js)

    if debug:
        print(f"locator_chain2={pformat(locator_chain2)}")

    return locator_chain2

def wrap_js_in_trap(js: str) -> str:
    js2 = f'''
try {{
{js}
}} catch (err) {{
    console.log(err.stack);
    return null;
}}
'''
    return js2


def js_list_to_locator_chain(js_list: list, **opt) -> list:
    locator_chain = []
    for js in js_list:
        locator_chain.append(f'js2element={js}')
    return locator_chain


def tp_click(element: WebElement, **opt):
    try:
        # this didn't improve
        #   print("first scrowIntoView")
        #   driver.execute_script("arguments[0].scrollIntoView();", element)
        #   print("then click")
        element.click()
    except ElementNotInteractableException:
        # use js to overcome this error
        #    selenium.common.exceptions.ElementNotInteractableException:
        #    Message: element not interactable
        print(f"\nseen ElementNotInteractableException. clicking with javascript ...\n")
        driver.execute_script("arguments[0].click();", element)
    except TimeoutException as ex:
        # so far two different scenarios and requires two different solutions.
        # 1. driver.get(url) often got the following error:
        #    selenium.common.exceptions.TimeoutException:
        #     Message: timeout: Timed out receiving message from renderer: 10.243
        #
        #     https://stackoverflow.com/questions/40514022/chrome-webdriver-produces-timeout-in-selenium
        print(ex.msg)
        print(f"\nseen 'TimeoutException receiving message from renderer' again? do driver.refresh() now. If this doesn't help, then set page_load_timeout longer.\n")
        driver.refresh()
        # 2. if the above doesn't help, we can increase the page_load_timeout.
        #    I defaulted it to 15 seconds, but for slow app like ServiceNow. we should set 30.
        #    I added an extra_args key for it.
    except WebDriverException as ex:
        # selenium.common.exceptions.WebDriverException: Message: target frame detached
        print(ex.msg)
        print(f"\nseen 'WebDriverException: Message: target frame detached' again? click() again\n")
        element.click()


js_by_key = {
    # https://stackoverflow.com/questions/27453617
    'shadowHost': '''
        var root = arguments[0].getRootNode();
        if (root.nodeType === Node.DOCUMENT_FRAGMENT_NODE && root.host != undefined) {
            return root.host;
        } else {
            return null;
        }
    ''',
    "attrs": """
        var items = {};
        for (index = 0; index < arguments[0].attributes.length; ++index) {
         items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value
        };
        return items;
    """,
    "xpath": """
        if (typeof(createXPathFromElement) !== 'function') {
            window.createXPathFromElement = function (elm, xpath_style) { 
                var segs = [];
                let allNodes = document.getElementsByTagName('*'); 
                
                if (!xpath_style || xpath_style != 'full') {
                    //if id is unique on document level, we return with id
                    if (elm.hasAttribute('id')) {                   
                        let documentUnique = 0; 
                        for (var n=0;n < allNodes.length;n++) { 
                            if (allNodes[n].hasAttribute('id') && allNodes[n].id == elm.id) {
                                documentUnique++;
                            }
                            if (documentUnique > 1) break; 
                        }; 
                        if ( documentUnique == 1) { 
                            segs.unshift(`id('${elm.id}')`);  // backtick for interpolation
                            return segs.join('/'); 
                        } 
                    }
                    
                    // do the same with class
                    // note the attribute name is inconsitent
                    //    element.hasAttribute('class')
                    //    element.className
                    if (elm.hasAttribute('class')) {                   
                        let documentUnique = 0; 
                        for (var n=0;n < allNodes.length;n++) { 
                            if (allNodes[n].hasAttribute('class') && allNodes[n].className == elm.className) {
                                documentUnique++;
                            }
                            if (documentUnique > 1) break; 
                        }; 
                        if ( documentUnique == 1) { 
                            segs.unshift(`class('${elm.className}')`); 
                            return segs.join('/'); 
                        } 
                    }
                }
                
                // now that neither id nor class is unique on document level
                for (; elm && elm.nodeType == 1; elm = elm.parentNode) 
                {     
                    // if id/class is unique among siblings, we use it to identify on sibling level
                    if (elm.parentNode) {                      
                        // childNodes vs children
                        //     childNodes include both elements and non-elements, eg, text
                        //     children include only elements.
                        // let siblings= elm.parentNode.childNodes;
                        let siblings= elm.parentNode.children;
                        
                        var siblingUnique = 0
                        for (var i= 0; i<siblings.length; i++) {
                            if (siblings[i].hasAttribute('id') && siblings[i].id == elm.id) {
                                siblingUnique++;
                            }
                            if (siblingUnique > 1) break; 
                        }; 
                        if (siblingUnique == 1) { 
                            // https://developer.mozilla.org/en-US/docs/Web/API/Element/localNam
                            //    <ecomm:partners> ....
                            // in the qualified name ecomm:partners, 
                            //    partners is the local name 
                            //    ecomm is the prefix
                            segs.unshift(`${elm.localName.toLowerCase()}[@id='${elm.id}']`);  
                            continue;
                        } 
                        
                        // check class
                        var siblingUnique = 0
                        for (var i= 0; i<siblings.length; i++) {
                            if (siblings[i].hasAttribute('class') && siblings[i].className == elm.className) {
                                siblingUnique++;
                            }
                            if (siblingUnique > 1) break; 
                        }; 
                        if (siblingUnique == 1) { 
                            segs.unshift(`${elm.localName.toLowerCase()}[@class='${elm.className}']`);  
                            continue;
                        } 
                    }
                    
                    // As neither id/class is unique on sibling level, we have to use position
                    let j = 1;
                    for (sib = elm.previousSibling; sib; sib = sib.previousSibling) { 
                        if (sib.localName == elm.localName)  j++; 
                    }
                    segs.unshift(`${elm.localName.toLowerCase()}[${j}]`);                    
                }                
                return segs.length ? '/' + segs.join('/') : null; 
            };
        }      
        return createXPathFromElement(arguments[0], arguments[1]);   
    """,
    # # https://stackoverflow.com/questions/4588119/get-elements-css-selector-when-it-doesnt-have-an-id
    "css": """
        if (typeof(getCssFullPath) !== 'function') {
            window.getCssFullPath = function (el) {
              var names = [];
              while (el.parentNode){
                if (el.id){
                  names.unshift('#'+el.id);
                  break;
                }else{
                  if (el==el.ownerDocument.documentElement) {
                    names.unshift(el.tagName);
                  } else {
                    for (var c=1,e=el;e.previousElementSibling;e=e.previousElementSibling,c++);
                    names.unshift(el.tagName+":nth-child("+c+")");
                  }
                  el=el.parentNode;
                }
              }
              return names.join(" > ");
            };
        }
        return getCssFullPath(arguments[0]);
    """,
}


def js_get(element: WebElement, key: str, **opt):
    global driver

    # https: // selenium - python.readthedocs.io / api.html  # module-selenium.webdriver.remote.webelement
    # element has no info about driver, therefore, we need two args there

    js = js_by_key.get(key, None)

    if js is None:
        raise RuntimeError(f'key={key} is not supported')

    # print(f"js={js}")

    if not driver or not element:
        return None

    extra_args = []

    if key == 'xpath':
        if opt.get('full', 0):
            # print full xpath
            extra_args.append('full')

    # use * to flatten list (array)
    return driver.execute_script(js, element, *extra_args)


def js_print(element: WebElement, key: str, **opt):
    print(f"{key}={pformat(js_get(element, key))}")


def js_print_debug(element: WebElement, **opt):
    global driver
    keys = ["attrs", "xpath"]
    print("specified element")
    for key in keys:
        js_print(element, key)
    print(f"tpdata = {pformat(getattr(element, 'tpdata', None))}")
    print("active element")
    active_element = driver.switch_to.active_element
    for key in keys:
        js_print(active_element, key)
    print(f"tpdata = {pformat(getattr(element, 'tpdata', None))}")


def test_basic():
    # if need to manually start Chrome (c1) on localhost with debug port 19999,
    #     From Linux,
    #         /usr/bin/chromium-browser --no-sandbox --disable-dev-shm-usage --window-size=960,540 \
    #         --user-data-dir=~/chrome_test --remote-debugging-port=19999
    #     From Cygwin or GitBash,
    #         'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe' --window-size=960,540 \
    #         --user-data-dir=C:/users/$USERNAME/chrome_test --remote-debugging-port=19999
    #     From cmd.exe, (have to use double quotes)
    #         "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe" --window-size=960,540 \
    #         --user-data-dir=C:/users/%USERNAME%/chrome_test --remote-debugging-port=19999

    driverEnv = SeleniumEnv("localhost:19999", verbose=1)
    driver = driverEnv.get_driver()
    print(f"driver.title={driver.title}")

    url = "http://www.google.com/"
    driver.get(url)
    try:
        # https://dev.to/endtest/a-practical-guide-for-finding-elements-with-selenium-4djf
        # in chrome browser, find the interested spot, right click -> inspect, this will bring up source code,
        # in the source code window, right click -> copy -> ...
        search_box = driver.find_element(By.NAME, "q")
    except NoSuchElementException as e:
        print(e)
    else:
        search_box.clear()
        search_box.send_keys("ChromeDriver")

        # the following are the same
        # search_box.send_keys(webdriver.common.keys.Keys.RETURN)
        search_box.submit()
        driverEnv.delay_for_viewer()  # Let the user actually see something!

    for tag_a in driver.find_elements(by=By.TAG_NAME, value="a"):
        link = None
        try:
            url = tag_a.get_attribute("href")
        # except NoSuchElementException as e:
        except NoSuchElementException:
            pass
        else:
            # print(f'url={url}')
            print(f"hostname = {urlparse(url).hostname}")

    # Selenium has no way to allow you start a webdriver and browser but only close the webdriver later.
    # When a webdriver starts a browser, it registers the closing action.
    # If we want to keep a browser running, we need to start it manually first, and then let the webdriver
    # to connect to it. As the webdriver didn't start the browser, it wouldn't register the closing action.
    # There were folks played with the code to only closing the webdriver without closing the browser, but
    # ends up with many zombie webdriver running in the background."
    # therefore, we close the driver explicitly.
    driver.quit()
    # driver.dispose()    # this will call driver.close()

    my_env = tpsup.envtools.Env()
    # list all the log files for debug purpose
    # use double quotes to close "C:/Users/.../selenium*" because bare / is a switch in cmd.exe.
    cmd = f"{my_env.ls_cmd} -ld \"{driverEnv.log_base}/\"seleninum*"
    print(cmd)
    os.system(cmd)

def follow(steps: list,  **opt):
    '''
    follow() is a recursive. it basic flow is: if ... then if ... then if ... then ...
    for example: [ 'click_xpath=/a/b', '"iframe', 'click_xpath=/c/d', 'string="hello world"', 'dump' ]
    By default, if any 'if' failed, we stop. For example, if 'click_xpath=/a/b' failed, we stop.
    If any 'then if' failed, we stop. For example, if 'iframe' failed, we stop.

    '''
    
    global locator_driver
    global driver
    global driver_url
    global last_element
    global return_levels

    update_locator_driver(**opt)

    # we support single-level block, just for convenience when testing using appium_steps
    # we don't support nested blocks; for nested block, use python directly
    block = []
    expected_blockend = None

    # use this to detect nested block of the same type, for example
    #     if      # if block depth = 1
    #         if      # if block depth = 2
    #         end_if  # if block depth = 1
    #         while   # while block depth = 1, if block depth = 1
    #         end_while # while block depth = 0, if block depth = 1
    #     end_if      # if block depth = 0

    block_depth = 0 # this needs to be a local var as follow() is recursive.

    condition = None
    blockstart = None
    negation = False

    debug = opt.get("debug", 0)
    verbose = opt.get("verbose", 0)

    ret = {'Success': False}

    if not steps:
        if debug or verbose:
            print(f'follow: steps are empty. return')
        return

    for step in steps:
        if debug:
            print(f"follow: step={pformat(step)}")

        step_type = type(step)

        # first handle control block. block start and block end are strings only.
        if block_depth > 0:
            # we are in a block
            
            if step_type == str and step == expected_blockend:
                # step matches the expected blockend
                block_depth -= 1

                if block_depth == 0:
                    # the outermost block is done
                    if debug:
                        print(f"follow: matched expected_blockend={expected_blockend}")
                    expected_blockend = None

                    print(f"follow: run block={block}, condition={condition}, block_depth={block_depth}")
                    if not block:
                        raise RuntimeError(f"block is empty")
                
                    # run_block() recursively calls follow()
                    run_block(blockstart, negation,
                                condition, block, **opt)
                else:
                    # we only encountered a nested block end
                    if debug:
                        print(f"follow: matched expected_blockend={expected_blockend}, but still in block_depth={block_depth}")

                    # we keep the nested block end in the block, so that we can recursively call run_block()
                    block.append(step)
            else:
                # this is not the expected blockend, we keep it in the block.
                block.append(step)

            # we are still in a block; we continue until we find the expected blockend.
            # we only build the block, we don't run it.
            # we will run the block after we find the expected blockend.
            continue
        
        # now that we are not in a block, we check whether this step is a start of a block
        if step_type == str:
            if m := re.match(r"\s*(while|if)(_not)?=(.+)", step):
                # we are starting a new block
                block_depth += 1
                blockstart = m.group(1)
                negation = m.group(2)
                condition = m.group(3)

                # if m := re.match(r"\s*(xpath|css|id)=(.+)", condition):
                #     tag, value, *_ = m.groups()
                #     if tag == 'id':
                #         condition = f"driver.find_element(By.ID, '''{value}''')"
                #     elif tag == 'xpath':
                #         if checkonly:
                #             print(f"check xpath={value}")
                #             try:
                #                 lxml.etree.XPath(value)
                #             except lxml.etree.XPathSyntaxError as e:
                #                 raise RuntimeError(
                #                     f"XPath syntax error in step={step}: {e}")
                #         condition = f"driver.find_element(By.XPATH, '''{value}''')"
                #     elif tag == 'css':
                #         condition = f"driver.find_element(By.CSS_SELECTOR, '''{value}''')"

                if negation:
                    expected_blockend = f"end_{blockstart}{negation}"
                else:
                    expected_blockend = f"end_{blockstart}"
                block = []
                if debug:
                    print(f"follow: blockstart={blockstart}, negation={negation}, condition={condition}, "
                        f"expected_blockend={expected_blockend}, block_depth={block_depth}")
                continue
        # now we are done with control block handling

        """
        non-control-block step can be a string or a more complex structure     

        complexity: string < dict (simple) < dict (parallel) < dict (chains)
        flexibility: string < dict (simple) < dict (parallel) < dict (chains)
    
        string 
            # string of a single locator, or multiple xpath/css/id separated by comma (searched in parallel).
                xpath=/a/b, 
                xpath=/a/c, 
                'xpath=/a/b,xpath=/a/c' # search in parallel, if either one is found, we are good. 
                click, 
                dump, ...
                note: only xpath/css/id can be in parallel (multiple locators separated by comma).

        # we could have also introduced 'list' for sequence flow, but sequence is already handled by follow() interface.
        #     ['click_xpath=/a/b,click_xpath=/c/d', 'string="hello world"', 'dump']

        dict
            # dict are mainly for real locators, eg, xpath/css/id/iframe/shadow/tab. 
            # we use dict to introduce parallelism.
            # other 'locators', eg, sleep, dump, wait, ... can be easily handled by string directly.
            {
                'type': 'simple',
                'action': {
                    'locator' : 'xpath=/a/b,xpath=/a/c', # 'simple' parallel, like the example on the left.
                                                         # 'simple' only means that syntax is simple.
                    #'Success' : 'code=print("found")', # optional. If either one is found, Do this. default is None
                    #'Failure' : 'print("not found")', # optional. If neither one is found, do this. default is RuntimeError
                }
            },

            {
                'type': 'parallel',
                'action': {
                    'paths' : [
                        # 'parallel' allows you to handle individual path differently - define 'Success' and 'Failure' for each path.
                        {
                            'locator' : 'xpath=//dhi-wc-apply-button[@applystatus="true"]',
                            'Success': 'code=' + '''action_data['error'] = "applied previously"''', # optional. default is None
                        },
                        {
                            'locator' : 'xpath=//dhi-wc-apply-button[@applystatus="false"]',
                            'Success': 'click',
                        },
                    ],
                    # 'action' level 'Success' and 'Failure' are optional.
                    #'Success' : 'code=print("found")', # optional. If either one is found, Do this. default is None
                    #'Failure' : 'print("not found")', # optional. If neither one is found, do this. default is RuntimeError
                }
            },
            
            {
                # chain is a list of list of locators in parallel.
                #     locators are in parallel, but the chain in each locator is in sequence.
                'type': 'chains',          
                'action': {
                    'paths' : [
                        {
                            'locator': [
                                'xpath=/html/body[1]/ntp-app[1]', 'shadow',
                                'css=#mostVisited', 'shadow',
                                'css=#removeButton2',  # correct on ewould be 'css=#removeButton'. we purposefully typoed
                            ],
                            'Success': 'code=print("found remove button")',
                        },
                        {
                            'locator': [
                                'xpath=/html/body[1]/ntp-app[1]', 'shadow',
                                'css=#mostVisited', 'shadow',
                                'css=#actionMenuButton'
                            ],
                            'Success': 'code=print("found action button")',
                        },
                        # 'action' level 'Success' and 'Failure' are optional.
                        # 'Success': 'code=print("found")',
                        # 'Failure': 'print("not found")',
                    ],
                },
            },
        ],

        'parallel' with a single path is the same as 'simple'.
        'chains' with a single path can be used to implement a 'sequence' of locators.

        'Success' and 'Failure' are optional. If not found, we raise RuntimeError by default.
        Therefore, define 'Failure' if you want to continue when not found.

        In 'parallel' and 'chains', we can define 'Success' and 'Failure' at 'action' level, but 
        we only define 'Success' at 'path' level, because the find...() function returns the first found element
        only. Therefore, we are not sure whether the other paths are found or not.

        we can make recurisve call of follow() at 'Success' and 'Failure' to handle the next step; but
        that could make 'locator_driver' and 'driver_url' confusing.

        The design of non-control-block flow is: if...then if ... then if ... then ....

        """

        result = {'Success': False}

        if step_type == str:
            result = locate(step, **opt)
        elif step_type == dict:
            result = locate_dict(step, **opt)
        else:
            raise RuntimeError(f"unsupported step type={step_type}, step={pformat(step)}")
        
        if debug:
            print(f"follow: result={pformat(result)}")

        if result is None:
            ret['Success'] = False
            break

        # copy result to ret
        ret['Success'] = result['Success']

        if not result['Success']:
            break

        if return_levels:
            break
    
    return ret

''' 
    locate() and locate_dict() are designed to be non-recursive, for reasons:
    - they are using global variables, therefore, recursive call would be confusing.
    - they are designed to be called by follow(), which is recursive.
    this is the reason why when we handle 'Success' and 'Failure', we call locate(), not call follow().
'''
def locate_dict(step: dict, **opt):
    dryrun = opt.get("dryrun", 0)
    interactive = opt.get("interactive", 0)
    debug = opt.get("debug", 0)
    verbose = opt.get("verbose", 0)
    checkonly = opt.get("checkonly", 0)
    
    global driver
    global driver_url
    global locator_driver
    global return_levels
    global last_element

    update_locator_driver(**opt)
    
    if debug:
        print(f"locate_dict: step={pformat(step)}")

    helper = {}  # interactivity helper
    if interactive:
        helper = {
            'd': ['dump page', dump,
                  {'driver': driver,
                      'output_dir': tpsup.tmptools.tptmp().get_nowdir(mkdir_now=0)}
                  # we delay mkdir, till we really need it
                  ],
        }

    ret = {'Success': False}

    locator_type = step.get('type', None)
    action = step.get('action', None)

    if locator_type == 'simple':
        # locator must be a string
        locator = action.get('locator', None)
        if type(locator) != str:
            raise RuntimeError(f"simple step locator must be a string, but got {type(locator)}, step={pformat(step)}")
        
        result = locate(locator, **opt)

        if result['Success']:
            # we found the element
            if 'Success' in action:
                locate(action['Success'], **opt) # we don't use follow() here, because we don't want to be recursive.
            ret['Success'] = True
        else:
            # we didn't find the element
            if 'Failure' in action:
                locate(action['Failure'], **opt)
            else:
                raise RuntimeError(f"element not found, step={pformat(step)}")
    elif locator_type == 'parallel':
        # paths must be a list
        paths = action.get('paths', None)
        if type(paths) != list:
            raise RuntimeError(f"parallel step paths must be a list, but got {type(paths)}, step={pformat(step)}")

        # concatenate all paths' locators into a single string so that we can call locate()
        # which take a string of locators, separated by comma.
        # locate() calls tp_find_element_by_paths() which can take multiple locators in parallel.
        locators_string = ",".join([path['locator'] for path in paths])

        result = locate(locators_string, **opt)

        # copy result to ret
        ret['Success'] = result['Success']

        if return_levels:
            return ret

        if result['Success']:
            # we found the element, the corresponing locator is in result['element'].tpdata
            tpdata = getattr(last_element, 'tpdata', None)
            path_index = tpdata['position']

            path = paths[path_index]
            if 'Success' in path:
                # path-level Found
                locate(path['Success'], **opt)
            if 'Success' in action:
                # action-level Found
                locate(action['Success'], **opt)
        else:
            # we didn't find the element
            if 'Failure' in action:
                # action-level NotFound
                locate(action['Failure'], **opt)
            else:
                raise RuntimeError(f"element not found, step={pformat(step)}")
    elif locator_type == 'chains':
        # paths must be a list
        paths = action.get('paths', None)
        if type(paths) != list:
            raise RuntimeError(f"chains step paths must be a list, but got {type(paths)}, step={pformat(step)}")

        # collect all the locators in all paths in a list and then call tp_find_element_by_chains()
        chains = []
        for path in paths:
            locator = path.get('locator', None)
            if type(locator) != list:
                raise RuntimeError(f"chains step locator must be a list, but got {type(locator)}, step={pformat(step)}")
            
            chains.append(locator)
        
        print(f"locate_dict: search for chains = {pformat(chains)}")

        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            # https://selenium-python.readthedocs.io/waits.html

            # for chains, we use "driver" instead of "locator_driver" because
            # tp_find_element_by_chains() adjust "locator_driver" internally.
            driverwait = WebDriverWait(driver, wait_seconds)

            # because we are using explicit wait call (WebDriverWait), 
            # we temporarily disable implicit wait in the tp_find_element_by_chains()
            locator_driver.implicitly_wait(0)
            
            finder = tp_find_element_by_chains(chains, **opt)

            element = None

            try:
                # wait.until() takes the object.
                # note: here we used finder, not finder(driver).
                element = driverwait.until(finder)
            except Exception as ex:
                print(f"locate failed. {ex}")
                print(f"matched_paths = {pformat(finder.matched_paths)}")

            # restore implicit wait
            driver.implicitly_wait(wait_seconds)

            if element:
                ret['Success'] = True
                last_element = element

                # Found. then find which path found the element
                tpdata = getattr(element, 'tpdata', None)
                path_index = tpdata['position']
                path = paths[path_index]

                if 'Success' in path:
                    # path-level Found
                    result = locate(path['Success'], **opt)
                if 'Success' in action:
                    # action-level Found
                    result = locate(action['Success'], **opt)             
            else:
                element = driver.switch_to.active_element
                last_element = element

                if 'Failure' in action:
                    # action-level NotFound
                    result = locate(action['Failure'], **opt)
                else:
                    raise RuntimeError(f"element not found, step={pformat(step)}")
    else:
        raise RuntimeError(f"unsupported locator_type={locator_type}, step={pformat(step)}")
    
    return ret

def update_locator_driver(**opt):
    global locator_driver
    global driver_url
    global driver

    helper = {}  # interactivity helper

    message = None
    if not locator_driver:
        message = "locator_driver was None"
    elif not driver_url:
        message = "driver_url was None"
    elif driver_url != driver.current_url:
        message = f"driver_url changed from {driver_url} to {driver.current_url}"
        
    if message:
        print(f"locate: update driver_url and locator_driver to driver because {message}")
        # hit_enter_to_continue(helper=helper)
        locator_driver = driver
        driver_url = driver.current_url

def tp_switch_to_frame(element: WebElement, **opt):
    '''
    the selenium.webdriver.switch_to.frame() is doesn't work perfectly
        for example, it doesn't update
                driver.current_url
                driver.title
        to test
            ptslnm url="file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html" sleep=1 get=url,title "xpath=/html[1]/body[1]/iframe[1]" "iframe" get=url,title "xpath=id('shadow_host')"
            ptslnm url="file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html" sleep=1 get=url,title "xpath=/html[1]/body[1]/iframe[1]" "tp_iframe" get=url,title "xpath=id('shadow_host')" 
        the ending url and title are different.
        'iframe' gave (wrong)
            file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html
            driver.title=Iframe over shadow
        'tp_iframe' gave (correct)
            file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html
            driver.title=child page
        the reason is that 'iframe' only works on http url, not on file:/// url.
        'tp_iframe' works on both because tp_iframe will force load the url after it caught the exception.
    selenium.webdriver.switch_to.frame() is implemented in
        sitebase/python3/venv/Windows/win10-python3.12/Lib/site-packages/selenium/webdriver/remote/switch_to.py: self._driver.execute(Command.SWITCH_TO_FRAME ...
        sitebase/python3/venv/Windows/win10-python3.12/Lib/site-packages/selenium/webdriver/remote/remote_connection.py: Command.SWITCH_TO_FRAME: ("POST", "/session/$sessionId/frame"),
        therefore, the real implementation is in chrome.exe.
        Chrome has the same user interface functionality as Chromium, but with a Google-branded color scheme. 
        Unlike Chromium, Chrome is not open-source.
        Therefore, we can look at chromium source code to see how it is implemented.
        The REST API source code is under https://github.com/chromium/chromium/blob/main/chrome/test/chromedriver/session.cc
        This seems to be implemented in C++, not in JavaScript. 
            void Session::SwitchToSubFrame(const std::string& frame_id,
                const std::string& chromedriver_frame_id) {
                std::string parent_frame_id;
                if (!frames.empty())
                    parent_frame_id = frames.back().frame_id;
                frames.push_back(FrameInfo(parent_frame_id, frame_id, chromedriver_frame_id));
                SwitchFrameInternal(false);
            }   
    '''
    js = '''
let e = arguments[0];
try {
    let iframe_inner = e.contentDocument || e.contentWindow.document;
    document = iframe_inner
    const current_origin = window.location.origin;
    console.log(`iframe stays in the same origin ${current_origin}`); // note to use backticks
} catch(err) {
    // print the error. note that console.log() is not available in Selenium.
    // console log is only available in browser's webtools console.
    console.log(err.stack);

    let iframe_src = e.getAttribute('src');
    //iframe_url = new URL(iframe_src);
    iframe_url = iframe_src;
    console.log(`iframe needs new url ${iframe_url}`);  // note to use backticks
    window.location.replace(iframe_url);
}

    '''

    global driver
    driver.execute_script(js, element)

def tp_switch_to_top(**opt):
    # get out of iframe
    # selenium has: driver.switch_to.default_content()
    js = '''
if (window.self !== window.top) {
  window.top.location.href = window.self.location.href; 
}
    '''
    global driver
    driver.execute_script(js)

def locate(locator: str, **opt):
    dryrun = opt.get("dryrun", 0)
    interactive = opt.get("interactive", 0)
    debug = opt.get("debug", 0)
    verbose = opt.get("verbose", 0)
    checkonly = opt.get("checkonly", 0)
    isExpression = opt.get("isExpression", 0) # for condtion test, we set isExpression=1, so that we get True/False.

    global locator_driver
    global driver
    global driver_url
    global wait_seconds
    global return_levels
    global last_element
    global jsr

    # we don't have a global var for active element, because
    #    - we can always get it from driver.switch_to.active_element
    #    - after we some action, eg, when 'click' is done, the active element is changed; 
    #      it needs to wait to update active element. Therefore, it is better to get it 
    #      from driver.switch_to.active_element in the next step (of locate()).

    ret = {'Success': False}

    helper = {}  # interactivity helper
    if interactive:
        helper = {
            'd': ['dump page', dump,
                  {'driver': driver,
                      'output_dir': tpsup.tmptools.tptmp().get_nowdir(mkdir_now=0)}
                  # we delay mkdir, till we really need it
                  ],
        }

    '''
    locator_driver vs original 'driver'
       - we introduce locator_driver because shadow_host.shadow_root is also a driver,
         we can call it shadow driver, but its locator can only see the shadow DOM,
         and only css locator is supported as of 2022/09/09.
       - locator_driver started as the original driver.
       - locator_driver will be shadow driver when we are in a shadow root.
       - locator_driver will be (original) driver after we switch_to an iframe, even if
         the iframe is under a shadow root.
       - every time driver_url changes, we should reset locator_driver to driver.
         driver_url can be changed not only by get(url), but also by click()
    shadow driver only has two attributes, just to support the separate DOM, the shadow DOM.
        - find_element
        - find_elements
    pycharm hint also only shows the above two attributes from a shadow driver.
    for example, shadow_host.shadow_root cannot
         - get(url)
         - switch_to
         - click()
         - execute_script()
    the difference can be seen in source code
        sitebase/python3/venv/Windows/win10-python3.12/Lib/site-packages/selenium/webdriver/remote/shadowroot.py
        sitebase/python3/venv/Windows/win10-python3.12/Lib/site-packages/selenium/webdriver/remote/webdriver.py
    '''

    update_locator_driver(**opt)
    
    # copied from old locate()
    if m := re.match(r"(url|url_accept_alert)=(.+)", locator):
        tag, url, *_ = m.groups()
        accept_alert = 0
        if tag == 'url_accept_alert':
            accept_alert = 1
        # some shortcuts for url
        if url == 'newtab':
            url = "chrome://new-tab-page"
        elif url == 'blank':
            url = "about:blank"

        print(f"locate: go to url={url}, accept_alert={accept_alert}")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            tp_get_url(url, accept_alert=accept_alert,
                    interactive=interactive)
            locator_driver = driver
            # the following doesn't work. i had to move it into tp_get_url()
            # try:
            #     driver_url = driver.current_url
            # except UnexpectedAlertPresentException as ex:
            #     # selenium.common.exceptions.UnexpectedAlertPresentException: Alert Text: {Alert text :
            #     # Message: unexpected alert open: {Alert text : }
            #     tpsup.tplog.print_exception(ex)
            #     alert = driver.switch_to.alert
            #     alert.accept()
            #     print("alert accepted")
            #     time.sleep(2)
            #     driver_url = driver.current_url
            driver_url = driver.current_url
            last_element = driver.switch_to.active_element
            ret['Success'] = True
    elif m := re.match(r"(code|python)=(.+)", locator, re.MULTILINE | re.DOTALL):
        _, code, *_ = m.groups()
        print(f"locate: run python code = {code}")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            # exec_into_globals(code, globals(), locals())
            if isExpression:
                # we are testing condition, we want to know True/False
                try:
                    ret['Success'] = eval(code)
                except Exception as e:
                    print(f"eval failed with exception={e}")
                    ret['Success'] = False
            else:
                exec_into_globals(code, globals(), locals())
                ret['Success'] = True # hard code to True for now
    elif m := re.match(r"(js.*?)=(.+)", locator, re.MULTILINE | re.DOTALL):
        js_directive, js, *_ = m.groups()

        # js_directive 
        #   source: 
        #       code: default to code
        #       file: read js code from a file
        #   target:
        #       element: default to element
        #       print: print the result of js
        #       targets can be combined, eg, js2elementprint, js2printelement
        #  
        # examples
        #     jsflie=filename.js
        #     js=js_code
        #     js2element=js_code
        #     jsfile2element=filename.js
        #     js2elementprint
        if '2' in js_directive:
            js_source, js_target = js_directive.split("2")
        else:
            js_source = js_directive
            js_target = None

        if js_source == 'jsfile':
            with open(js) as f:
                js = f.read()

        print(f"locate: execute js={js}\n")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            jsr = driver.execute_script(js)
            if 'element' in js_target:
                last_element = jsr
            else:
                last_element = driver.switch_to.active_element

            if 'print' in js_target:
                print(jsr)
            
            # https://stackoverflow.com/questions/37791547
            # https://stackoverflow.com/questions/23408668
            # last_iframe = driver.execute_script("return window.frameElement")
            # # pause to confirm
            # print(f"last_iframe={last_iframe}")
            # hit_enter_to_continue(helper=helper)

            ret['Success'] = True
    elif m := re.match(r"tab=(.+)", locator):
        count_str, *_ = m.groups()
        count = int(count_str)
        print(f"locate: tab {count} times")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            driver.switch_to.active_element.send_keys(Keys.TAB * count)
            last_element = driver.switch_to.active_element
            ret['Success'] = True
    elif m := re.match(r"shifttab=(.+)", locator):
        count_str, *_ = m.groups()
        count = int(count_str)
        print(f"locate: tab backward (shift+tab) {count} times")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            ac = ActionChains(driver)
            ac.key_down(Keys.SHIFT)
            for i in range(0, count):
                ac.send_keys(Keys.TAB)
            ac.key_up(Keys.SHIFT)
            ac.perform()
            last_element = driver.switch_to.active_element
            ret['Success'] = True
    elif locator == "shadow":
        print(f"locate: switch into shadow_root")
        # if the element is found by finde_element_by_xpath/css/id, it
        # may not be the active element. therefore, we use last_element.
        # element = driver.switch_to.active_element
        element = last_element
        try:
            if element.shadow_root:
                pass
        except NoSuchShadowRootException:
            print(f'locate: no shadow root under this element')
            return
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            locator_driver = element.shadow_root  # shadow_driver is a webdriver type
            # last_element = element # last element is unchanged. this is different from iframe.
            ret['Success'] = True
    elif m := re.match(r"(iframe|tp_iframe|parentIframe|top|tp_top)", locator):
        iframe = m.group(1)
        print(f"locate: switch into {iframe}")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            # the element may not be the active element. It could just be the element 
            # found from find_element_by_xpath(). therefore, we use last_element
            # element = driver.switch_to.active_element
            element = last_element

            '''
            we cannot use locator_driver to swith iframe when locator_driver is a shadow root.
              locator_driver.switch_to.frame(element)
              AttributeError: 'ShadowRoot' object has no attribute 'switch_to'
            Therefore, we use (original) driver

            the selenium.webdriver.switch_to.frame() is doesn't work perfectly
                for example, it doesn't update
                     driver.current_url
                     driver.title
            to test
                ptslnm url="file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html" sleep=1 get=url,title "xpath=/html[1]/body[1]/iframe[1]" "tp_iframe" get=url,title "xpath=id('shadow_host')"
                ptslnm url="file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html" sleep=1 get=url,title "xpath=/html[1]/body[1]/iframe[1]" "iframe" get=url,title "xpath=id('shadow_host')" 
            the ending url and title are different.
            'iframe' gave (wrong)
                file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html
                driver.title=Iframe over shadow
            'tp_iframe' gave (correct)
                file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html
                driver.title=child page
            the reason is that 'iframe' only works on http url, not on file:/// url.
            'tp_iframe' works on both because tp_iframe will force load the url after it caught the exception.
            '''
   
            if iframe == "iframe":
                # we keep the selenium way here, in case the problem is fixed in the future.
                driver.switch_to.frame(element)
            elif iframe == "parentIframe":
                driver.switch_to.parent_frame()   
            elif iframe == "top":
                driver.switch_to.default_content()
            elif iframe == "tp_top":
                tp_switch_to_top()
            else:
                # tp_frame
                tp_switch_to_frame(element, **opt)
            
            # once we switch into an iframe, we should use original driver to locate    
            locator_driver = driver
            driver_url = driver.current_url
            
            # switch info iframe change the last element to active element.
            # this is different from when we switch into shadow root.
            last_element = driver.switch_to.active_element

            ret['Success'] = True
    elif m1 := get_locator_compiled_path1().match(locator):
        ptype, paths_string = m1.groups()
        # default to strip blanks: space, tab, newline ...
        paths_string = paths_string.strip()

        type_paths = []
        while m2 := get_locator_compiled_path2().match(paths_string):
            path, type2 = m2.groups()
            end_pos = m2.end()

            # rstrip():  right (rear) strip();
            # lstrip: left (leading) strip;
            # strip(): both.
            # default to strip blanks: space, tab, newline ...
            # here we also strip the ending comma.
            # todo: find a better way to strip endinng space and comma
            # print(f'path1={pformat(path)}')
            path = path.rstrip().rstrip(",").rstrip()
            # print(f'path2={pformat(path)}')

            type_paths.append([ptype, path])

            ptype = type2  # to be used in next round
            paths_string = paths_string[end_pos:]

        path = paths_string  # leftover is a path
        # todo: find a better way to strip endinng space and comma
        # print(f'path1={pformat(path)}')
        path = path.rstrip().rstrip(",").rstrip()
        # print(f'path2={pformat(path)}')

        type_paths.append([ptype, path])

        print(f"locate: search for paths = {pformat(type_paths)}")

        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            # here we use locator_driver, because tp_find_element_by_paths() 
            # will call find_element_by ... directly which needs a locator_driver.
            driverwait = WebDriverWait(locator_driver, wait_seconds)  # seconds

            finder = tp_find_element_by_paths(type_paths, **opt)

            # because we are using explicit wait call (WebDriverWait), 
            # we temporarily disable implicit wait in the tp_find_element_by_paths()
            driver.implicitly_wait(0)
            # don't use locator_driver above, because implicit_wait() is not available
            # in shadow_root (driver).
            # locator_driver.implicitly_wait(0)

            element = None
            # this is needed; otherwise, if element is defined, a failed 'try' below
            # will not set element to None.

            try:
                # https://selenium-python.readthedocs.io/waits.html
                element = driverwait.until(finder)
                # element = driverwait.until(find_element_by_xpath('//input[@name="q"]'))
                last_element = element
                ret['Success'] = True

                # which path found the element is saved in element.tpdata
            except Exception as ex:
                print(f"locate failed: {pformat(ex)}")

            # restore implicit wait but
            # don't use locator_driver here, because implicit_wait() is not available
            # in shadow_root (driver).
            # locator_driver.implicitly_wait(0)
            driver.implicitly_wait(wait_seconds)
    # end of old locate()
    # the following are from old send_input()
    elif m := re.match(r"sleep=(\d+)", locator):
        ret['Success'] = True # hard code to True
        value, *_ = m.groups()
        print(f"locate: sleep {value} seconds")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            time.sleep(int(value))
    elif m := re.match(r"hover=(.+)", locator):
        seconds_str, *_ = m.groups()
        seconds = int(seconds_str)
        print(f"locate: hover {seconds} seconds")

        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            if not last_element:
                raise RuntimeError("no element to hover")
            ActionChains(driver).move_to_element(
                last_element).pause(seconds).perform()
            # this action should not change the active element
            ret['Success'] = True
    elif m := re.match(r"string=(.+)", locator, re.MULTILINE | re.DOTALL):
        value, *_ = m.groups()
        print(f"locate: string={value}")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            element = driver.switch_to.active_element
            element.send_keys(value)
            last_element = element
            ret['Success'] = True
    elif m := re.match(r"clear_attr=(.+)", locator):
        # even if only capture group, still add *_; other attr would become list, not scalar
        attr, *_ = m.groups()
        print(f"locate: clear {attr}")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            element = driver.switch_to.active_element
            value = element.get_attribute(attr)
            if not value is None:
                length = len(value)
                key = "backspace"
                print(f"typing {key} {length} times")
                element.send_keys(
                    Keys.__getattribute__((Keys, key.upper())) * length
                )
            last_element = element
            ret['Success'] = True
    elif m := re.match(r"is_attr_empty=(.+)", locator):
        attr, *_ = m.groups()
        print(
            f"locate: check whether {attr} is empty.")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            # the checked element may not be the active element.
            # element = driver.switch_to.active_element
            if not last_element:
                raise RuntimeError("no element to check")
            value = last_element.get_attribute(attr)
            print(f'{attr} = "{value}"')
            if not (value is None or value == ""):
                raise RuntimeError(f"{attr} is not empty")
            ret['Success'] = True
    elif m := re.match(r"key=(.+?)(,\d+)?$", locator, re.IGNORECASE):
        '''
        example:
            key=enter
            key=enter,3
        '''
        key, count_str = m.groups()

        if count_str:
            count = int(count_str[1:])
        else:
            count = 1
        
        print(f"locate: type {key} {count} times")

        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            element = driver.switch_to.active_element
            element.send_keys(Keys.__getattribute__(
                Keys, key.upper()) * count)
            last_element = element
            ret['Success'] = True
    elif locator == 'click' or locator == 'tp_click':
        print(f"locate: click")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            # the to-be-clicked element may not be the active element, for
            # example, we just found a element by find_element_by_xpath(),
            # that element is not the active element.
            # but after we click it, it will be active.
            # element = driver.switch_to.active_element
            # element.click()
            if not last_element:
                raise RuntimeError("no element to click")
            
            if locator == 'click':
                # we keep the selenium way here, in case the problem is fixed in the future.
                last_element.click()
            else:
                # tp_click() is a wrapper of click() to handle the case when the element is not clickable.
                tp_click(last_element)
            ret['Success'] = True
    elif m := re.match(r"select=(value|index|text),(.+)", locator):
            attr, string = m.groups()
            print(f'locate: select {attr} = "{string}"')
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                # the selected element may not be the active element.
                # for example, we just found a element by find_element_by_xpath(),
                # that element is not the active element.
                # but after we select it, it will be active.
                # element = driver.switch_to.active_element

                if not last_element:
                    raise RuntimeError("no element to select")
                se = Select(last_element)
                if attr == "value":
                    se.select_by_value(string)
                elif attr == "index":
                    se.select_by_index(int(string))
                else:
                    # attr == 'text'
                    se.select_by_visible_text(string)
                last_element = se # todo: or keep old last_element?
                ret['Success'] = True      
    elif m1 := re.match(r"(?:\n|\r\n|\s?)*gone_(xpath|css)=(.+)",
                        locator, re.MULTILINE | re.DOTALL):
        ptype, paths_string = m1.groups()

        type_paths = []
        while m2 := re.match(r"(.+?)(?:\n|\r\n|\s?)*,(?:\n|\r\n|\s?)*gone_(xpath|css)=",
                                paths_string, re.MULTILINE | re.DOTALL):
            path, ptype2 = m2.groups()
            end_pos = m2.end()

            type_paths.append([ptype, path])
            ptype = ptype2  # to be used in next round
            paths_string = paths_string[end_pos:]

        type_paths.append([ptype, paths_string])

        print(
            f"locate: wait {wait_seconds} seconds for elements gone, paths = {pformat(type_paths)}")

        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            e = None
            i = 0

            # temporarily set implicit wait to 0, so that find_element() will not wait
            driver.implicitly_wait(0)

            while i < wait_seconds:
                i = i + 1
                # wait at least a second to let the element show up
                time.sleep(1)
                for ptype, path in type_paths:
                    e = None
                    if ptype == "xpath":
                        try:
                            e = driver.find_element(By.XPATH, path)
                            break
                        except Exception:
                            pass
                    else:
                        # ptype == 'css'
                        try:
                            e = driver.find_element(By.CSS_SELECTOR, path)
                            break
                        except Exception:
                            pass
                else:
                    if i > 1:
                        # this is the normal exit point from the for loop
                        print(f"locate: all paths gone in {i} seconds")
                        ret['Success'] = True
                        break
            if e:
                js_print_debug(e)
                raise RuntimeError(f"not all paths gone in {i} seconds")
            
            # restore implicit wait
            driver.implicitly_wait(wait_seconds)

            # don't change last_element
    elif m := re.match(r"dump_(element|iframe|page|all)=(.+)", locator):
        scope, output_dir, *_ = m.groups()
        print(f"locate: dump {scope} to {output_dir}")
        '''
        about the scope:
            element: dump the last element's info
            dom:     dump everything about the innest iframe or shadow dom of the element.
            page:    dump the whole page.
            all:     dump all scopes: 'element', 'dom', 'page', into separate subdirs.

            for example, when we run 
            ptslnm_locate -rm -debug "file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html" "C:/Users/tian/dumpdir2" xpath=//iframe[1] iframe "xpath=//body/p"
            the chain is: xpath=//iframe[1] iframe "xpath=//body/p"

            if we dump_element, we dump the last element, which is the <p> element. source.html only contains the <p> element.
            if we dump_dom, we dump the shadow dom of the <p> element. source.html only contains the iframe dom which contains the <p> element.
            if we dump_all, we dump the whole page. source.html contains the whole page.

            dump_element and dump_dom are reliable because they are not affected by the driver's state (in iframe/shadow or not).
            dump_page is unreliable or have side effect because it needs to switch driver to the original driver.
        '''

        # output_dir can be from both **opt and step, to avoid the multiple-values error,
        # we group output_dir into **opt, allowing override kwargs

        # save a copy of README.txt
        readme_file = f"{output_dir}/README.txt"

        os.makedirs(output_dir, exist_ok=True)  # this is mkdir -p

        with open(readme_file, "w", encoding="utf-8") as readme_fh:
            readme_fh.write(dump_readme)
            readme_fh.close()
        
        if scope == 'element' or scope == 'all':
            subdir = f"{output_dir}/element"
            print()
            print(f"locate: dump element to {subdir}")

            # element = driver.switch_to.active_element
            # if element is None:
            if last_element:
                dump(element=last_element, **{**opt, 'output_dir': f"{subdir}"})

        if scope == 'iframe' or scope == 'all':
            subdir = f"{output_dir}/iframe"
            print()
            print(f"locate: dump iframe to {subdir}")

            # we don't use locator_driver, because we got error
            #    AttributeError: 'ShadowRoot' object has no attribute 'page_source'
            # dump(locator_driver, **{**opt, 'output_dir': f"{subdir}"})
            dump(**{**opt, 'output_dir': f"{subdir}"})

        # we put 'page' and 'all' at the end, because they need to switch driver to original driver.
        if scope == 'page' or scope == 'all':
            subdir = f"{output_dir}/page"
            print()
            print(f"locate: dump page to {subdir}")
                
            # switch driver to original driver, because dump() needs to dump the whole page.
            # driver.switch_to.default_content()
            tp_switch_to_top()

            dump(**{**opt, 'output_dir': f"{subdir}"})

            # # switch back to the last iframe
            # if last_iframe:
            #     driver.switch_to.frame(last_iframe)

        ret['Success'] = True
    elif m := re.match(r"we_return()$|we_return=(\d+)", locator):
        ret['Success'] = True # hard code to True for now

        we_return, *_ = m.groups()

        # default return levels is 999, ie, return all levels
        if we_return == "":
            return_levels = 999
        else:
            return_levels = int(we_return)

        print(f"locate: we_return={we_return}, return_levels={return_levels}")

    # end of old send_input()

    # the following are new
    elif m := re.match(r"wait=(\d+)", locator):
        ret['Success'] = True # hard code to True

        # implicit wait
        value, *_ = m.groups()
        print(f"locate: set wait {value} seconds for both implicit and explicit wait")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            # explicit wait is set when we call WebDriverWait(driver, wait_seconds).
            # explicit wait is done per call (WebDriverWait()).
            # As we are not calling WebDriverWait() here, we only set the global variable,
            # so that it can be used when we call WebDriverWait() in the future.
            wait_seconds = int(value)

            # driver.implicitly_wait() only set the implicit wait for the driver, 
            # affect all find_element() calls right away.
            # implicit wait is done once per session (driver), not per call.
            # selenium's default implicit wait is 0, meaning no wait.
            driver.implicitly_wait(wait_seconds)

    elif locator == 'refresh':
        print(f"locate: refresh driver")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            driver.refresh()
            locator_driver = driver
            last_element = None

    elif m := re.match(r"comment=(.+)", locator, re.MULTILINE | re.DOTALL):
        ret['Success'] = True # hard code to True for now
        commnet, *_ = m.groups()
        print(f"locate: comment = {commnet}")
    elif m := re.match(r"consolelog", locator):
        ret['Success'] = True
        print(f"locate: print console log")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            print_js_console_log()
    elif m := re.match(r"pagewait=(\d+)", locator):
        ret['Success'] = True
        page_load_timeout, *_ = m.groups()
        print(f"locate: set page_load_timeout to {page_load_timeout} seconds")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            # set timeout
            # https://stackoverflow.com/questions/17533024/how-to-set-selenium-python-webdriver-default-timeout
            driver.set_page_load_timeout(page_load_timeout)
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
    elif m := re.match(r"get=(.+)", locator):
        ret['Success'] = True
        keys_string = m.groups()[0]
        keys = keys_string.split(",")
        print(f"locate: get property {keys}")
        if interactive:
            hit_enter_to_continue(helper=helper)
        for key in keys:
            if not dryrun:
                if key == 'timeouts':
                    # https://www.selenium.dev/selenium/docs/api/py/webdriver_chrome/selenium.webdriver.chrome.webdriver.html
                    # https://www.selenium.dev/selenium/docs/api/java/org/openqa/selenium/WebDriver.Timeouts.html
                    print(f'implicit_wait={driver.timeouts.implicit_wait}')
                    print(f'page_load_timeout={driver.timeouts.page_load}')
                    print(f'script_timeout={driver.timeouts.script}')
                elif key == 'title':
                    title = driver.title
                    print(f'driver.title={title}')
                elif key == 'url':
                    # iframe will change the url.
                    url = driver.current_url
                    print(url)
                else:
                    raise RuntimeError(f"unsupported key={key}")

    else:
        raise RuntimeError(f"unsupported 'locator={locator}'")
    
    return ret

# def js_get_shadowhost(element: WebElement, **opt):
#     # https://stackoverflow.com/questions/27453617
#     js = '''
#     var root = arguments[0].getRootNode();
#     if (root.nodeType === Node.DOCUMENT_FRAGMENT_NODE && root.host != undefined) {
#         return root.host;
#     } else {
#         return null;
#     }
#     '''
#     return driver.execute_script(js, element)


def run_block(blockstart: str, negation: str,  condition: str, block: list, **opt):
    # we separate condition and negation because condition test may fail with exception, which is
    # neither True or False.  In this case, we want to know the condition test failed.
    verbose = opt.get('verbose', False)
    debug = opt.get('debug', False)
    ret = {'Success': False, 'executed': False, 'element': None}

    global return_levels

    if blockstart == 'while':
        while True:
            result = if_block(negation, condition, block, **opt)
            if debug:
                print(f"run_block: result={result}")
            if not result['executed']:
                break

            # only while-loop can be broken.
            if return_levels:
                if debug:
                    print(f"run_block: return_levels={return_levels}, break the while loop")
                # reduce return_levels by 1
                return_levels = return_levels - 1
                break
    elif blockstart == 'if':
        result=if_block(negation, condition, block, **opt)

    ret['Success'] = result['Success']
    ret['executed'] = result['executed']

    return ret


def if_block(negation: str,  condition: str, block: list, **opt):
    # we separate condition and negation because condition test may fail with exception, which is
    # neither True or False.  In this case, we want to know the condition test failed.

    verbose = opt.get('verbose', False)
    checkonly = opt.get('checkonly', False)

    ret = {'Success': False, 'executed': False}

    # try:
    #     result['Success'] = eval(condition)
    # except Exception as e:
    #     # if verbose:
    #     print(f"if_block(): condition test failed with exception={e}")
    #     result['Success'] = False
    result = locate(condition, isExpression=True, **opt)

    if result['Success'] and negation:
        print(
            f"if_not_block: condition '{condition}' is true, but negated, block is not executed")
        executed = False
    elif not result['Success'] and not negation:
        print(f"if_block: condition '{condition}' is not true, block is not executed")
        executed = False
    else:
        executed = True

    ret['executed'] = executed

    if executed:
        if not checkonly:
            # recursively calling follow() to run the block
            try:
                result = follow(block, **opt)
            except Exception as e:
                print(f"if_block: follow() failed with exception={pformat(e)}")
                return ret
    
            if result:
                ret['Success'] = result['Success']

    return ret

# pre_batch and post_batch are used to by batch.py to do some setup and cleanup work
# known is only available in post_batch, not in pre_batch.


def pre_batch(all_cfg, known, **opt):
    print("")
    print('running pre_batch()')
    if all_cfg["resources"]["selenium"].get('driver', None) is None:
        method = all_cfg["resources"]["selenium"]["driver_call"]['method']
        kwargs = all_cfg["resources"]["selenium"]["driver_call"]["kwargs"]
        all_cfg["resources"]["selenium"]['driver'] = method(**kwargs)
        print("pre_batch(): driver is created")
    print("pre_batch(): done")
    print("--------------------------------")
    print("")

    # init global variables
    global driver
    driver = all_cfg["resources"]["selenium"]["driver"]


def post_batch(all_cfg, known, **opt):
    print("")
    print("--------------------------------")
    print(f"running post_batch()")
    if 'driver' in all_cfg["resources"]["selenium"]:
        print(f"we have driver, quit it")
        driver = all_cfg["resources"]["selenium"]["driver"]
        driver.quit()
        print("")

        print(f"list all the log files for debug purpose")
        driverEnv = driver.driverEnv
        my_env = driverEnv.env
        if my_env.isWindows:
            cmd = f"{my_env.ls_cmd} \"{driverEnv.log_base}\\selenium*\""
        else:
            cmd = f"{my_env.ls_cmd} -ld \"{driverEnv.log_base}\"/selenium*"
        print(cmd)
        os.system(cmd)
        print("")

        # delete a key from a dict, we can use either del or pop
        #    se d.pop if you want to capture the removed item, like in item = d.pop("keyA").
        #    Use del if you want to delete an item from a dictionary.
        #        if thekey in thedict: del thedict[thekey]
        del all_cfg["resources"]["selenium"]["driver"]

    print(f"check if chromedriver is still running")
    my_env = tpsup.envtools.Env()
    if tpsup.pstools.ps_grep("chromedriver", printOutput=1):
        print(f"seeing leftover chromedriver, kill it")
        if my_env.isWindows:
            cmd = f"pkill chromedriver"
        else:
            # -f means match the full command line. available in linux, not in windows
            cmd = f"pkill -f chromedriver"
        print(cmd)
        os.system(cmd)


tpbatch = {
    'pre_batch': pre_batch,
    'post_batch': post_batch,
    "extra_args": {
        'headless': {
            "switches": ["--headless"],
            "default": False,
            "action": "store_true",
            "help": "run in headless mode",
        },
        'humanlike': {
            "switches": ["--humanlike"],
            "default": False,
            "action": "store_true",
            "help": "add some random delay to make it more humanlike",
        },
        'host_port': {
            "switches": ["-hp", "--host_port"],
            "default": "auto",
            "action": "store",
            "help": "connect to a browser at host:port.  default is auto, which means to start a new browser",
        },
        'log_base': {
            "switches": ["-log_base"],
            "default": None,
            "action": "store",
            "help": "base dir for selenium_browser log files, default to home_dir",
        },
    },
    "resources": {
        "selenium": {
            # "method": tpsup.seleniumtools.get_driver,
            "method": get_driver,
            # "cfg": {},
            "init_resource": 0,  # delay init until first use
        },
    },
}


def main():
    # test_basic()
    pass


if __name__ == "__main__":
    main()
