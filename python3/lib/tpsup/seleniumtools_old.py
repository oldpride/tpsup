import os
import re
import shlex
import shutil
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
from tpsup.locatetools_old import handle_break,get_defined_locators

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

from tpsup.interactivetools import hit_enter_to_continue
from tpsup.exectools import exec_into_globals, multiline_eval

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

# run these locators before or after each step
debuggers = {
    'before': [],
    'after': [],
}

# dom stack, to keep track of the dom tree: iframe, shadow
# we update domstack only in locate(), and use it track our 
# current dom at locate() level.
# we don't use it to track dom in other functions. 
#     - we don't use it to track dom in dump() because in dump() the dom switch
#       is very predictable, between child and parent, and self-contained.
#     - we don't use it to track dom in replay_domstack() because we normally
#       use it to replay the global domstack anyway.
domstack = []

'''
    iframestack vs domstack
        iframestack is a list of iframe urls starting from current iframe to the top iframe.
        domstack    is a list of iframe and shadow starting from top to current iframe or shadow.

        iframestack is built by js in realtime. There is no global variable for iframestack.
        domstack    is accumulated into a global variable as we go deeper into iframe or shadow.
    why do we need both?
        one reason is that we need to them to cross check each other.
'''
def print_iframestack(**opt):
    global driver
    print("print_iframestack:")
    iframestack = driver.execute_script(js_by_key['iframestack'])
    ident = ""
    for item in iframestack:
        ident += "  "
        url = item['url']
        print(f"{ident}{url}")
    
def print_domstack(**opt):
    # this function is domstack safe, meaning it doesn't change the domstack, neither changes driver (dom)
    global domstack
    global driver

    print("print_domstack:")
    ident = ""
    for item in reversed(domstack):
        ident += "  "
        dom_type = item['type']
        url = item['url']
        print(f"{ident}{dom_type}: {url}")

def replay_domstack(domstack2: list, **opt):
    # replay domstack from the beginning
    # this doesn't change global domstack.
    global driver
    global locator_driver
    global last_element

    # go back to the beginning
    driver.switch_to.default_content()
    locator_driver = driver

    for item in domstack2:
        dom_type = item['type']
        url = item['url']
        element = item['element']
        print(f"replay {dom_type}: {url}")
        if dom_type == 'iframe':
            driver.switch_to.frame(element)
            locator_driver = driver
            last_element = driver.switch_to.active_element
        elif dom_type == 'shadow':
            shadow_root = element.shadow_root
            locator_driver = shadow_root
        else:
            raise RuntimeError(f"unsupported dom_type={dom_type}")

def get_domstack(request: str, **opt):
    '''
    if request is 'last_shadow', this returns {
        item: {
            type: 'shadow',
            url: '...',
            element: ...
        },
        domstack: [ ... ]
        }
        or None if no shadow found.
    
    if request is 'last_iframe', this returns {
        item: {
            type: 'iframe',
            url: '...',
            element: ...
        },
        domstack: [ ... ]
        }
        or None if no iframe found.
    '''
    global domstack
    global driver

    if m := re.match(r'last_(shadow|iframe)', request):
        request_type = m.group(1)
        domstack2 = domstack.copy()
        for item in reversed(domstack):
            if item['type'] == request_type:
                return {
                    'item': item,
                    'domstack': domstack2
                }
            else:
                domstack2.pop()
        return None
    else:
        raise RuntimeError(f"unsupported request={request}")    

diagram = '''
+----------+      +--------------+     +----------------+
| selenium +----->+ chromedriver +---->+ chrome browser +---->internet
+----------+      +--------------+     +----------------+
'''

class SeleniumEnv:
    def __init__(self, host_port: str = 'auto', **opt):
        # print(pformat(opt))
        # exit(1) 
        global cmd
        self.driver:webdriver.Chrome = None 
        self.host_port = host_port
        self.debug = opt.get("debug", 0)
        self.verbose = opt.get("verbose", self.debug) # verbose is more common (lighter) than debug
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

        if opt.get("cleanLog", 0) or opt.get("cleanQuit", 0):
            self.cleanLog()
            if opt.get("cleanQuit", 0):
                exit(0)

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

        if self.debug:
            # print(sys.path)
            log_FileFuncLine(f"pwd={os.getcwd()}")
            log_FileFuncLine(f'PATH={os.environ["PATH"]}')

            self.print_running_drivers()

            if self.debug > 1:
                if self.env.isLinux or self.env.isGitBash or self.env.isCygwin:
                    # display the beginning of the log file as 'tail' only display the later part
                    # use /dev/null to avoid error message in case the log file has not been created
                    cmd = f"cat /dev/null {self.driverlog}"
                    log_FileFuncLine(f"cmd={cmd}\n")
                    os.system(cmd)

                    # --pid PID  exits when PID is gone
                    # -F         retry file if it doesn't exist
                    cmd = f"tail --pid {os.getpid()} -F -f {self.driverlog} &"
                    log_FileFuncLine(f"cmd={cmd}")
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

            log_FileFuncLine(f"check browser port at {host_port}") 
            self.connected_existing_browser = False
            (host, port) = host_port.split(":", 1)
            if is_tcp_open(host, port):
                log_FileFuncLine(f"{host_port} is open. let chromedriver to connect to it")
            else:
                raise RuntimeError(f"browser host_port={host_port} is not open.\n")

        if host_port == "auto":
            log_FileFuncLine("chromedriver will auto start a browser and pick a port")

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
                log_FileFuncLine(" in headless mode\n")
        else:
            host, port = host_port.split(":", 1)
            self.browser_options.add_argument(
                f"--remote-debugging-port={port}")
            # self.browser_options.add_argument(f'--remote-debugging-address=127.0.0.1')

            if host.lower() != "localhost" and host != "127.0.0.1" and host != "":
                if self.dryrun:
                    log_FileFuncLine("cannot connect to remote browser, but this is dryrun, so we continue")
                else:
                    raise RuntimeError("cannot connect to remote browser.")
            else:
                log_FileFuncLine("cannot connect to an existing local browser. we will start up one.")
                self.browser_options.binary_location = get_browser_path()

                if self.headless:
                    self.browser_options.add_argument("--headless")
                    log_FileFuncLine("in headless mode")

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

        # https://stackoverflow.com/questions/79313080
        # self.browser_options.add_argument("--disable-popup-blocking")

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

        log_FileFuncLine(f"browser_options.arguments = {pformat(self.browser_options.arguments)}")
        log_FileFuncLine(f"driver.args = {pformat(self.driver_args)}")

        # rotate the log file if it is bigger than the size.
        tpsup.logtools.rotate_log(
            self.driverlog, size=1024 * 1024 * 10, count=1)

        # make sure chromedriver is in the PATH
        # selenium 4.10+ need to wrap executable_path into Service
        # https://stackoverflow.com/questions/76428561
        self.driver_service = ChromeDriverService(
            # Service decides how driver starts and stops
            executable_path=self.driver_exe,
            log_path=self.driverlog,
            service_args=self.driver_args,  # for chromedriver
        )
        
        log_FileFuncLine(f"driverEnv is created. driver will be created when needed by calling driverEnv.get_driver()")
        # if self.dryrun:
        #     log_FileFuncLine("this is dryrun, therefore, we don't start a webdriver, nor a browser")
        #     # even if it is dryrun, we still have a SeleniumEnv
        # else:
        #     self.driver = webdriver.Chrome(
        #         service=self.driver_service,
        #         options=self.browser_options,
        #     )
        #     log_FileFuncLine("started driver")

        #     self.driver.driverEnv = self  # monkey patching for convenience

    def clean(self):
        # remove driver log and chromedir
        for f in [self.driverlog, self.chromedir]:
            log_FileFuncLine(f"removing {f}")
            try:
                shutil.rmtree(f)
            except FileNotFoundError:
                if self.debug:
                    log_FileFuncLine(f"{f} not found")
            except NotADirectoryError:
                if self.debug:
                    os.remove(f)

    def get_driver(self) -> webdriver.Chrome:
        if not self.driver:
            self.driver = webdriver.Chrome(
                service=self.driver_service,
                options=self.browser_options,
            )
            log_FileFuncLine("started driver")
            self.driver.driverEnv = self  # monkey patching for convenience            
        return self.driver
    
    def get_home_dir(self) -> str:
        return self.env.home_dir

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

driverEnv: SeleniumEnv = None
def get_driverEnv(**args) -> SeleniumEnv:
    global driverEnv

    if not driverEnv:
        driverEnv = SeleniumEnv(**args)
    return driverEnv

def get_driver(**args) -> webdriver.Chrome:
    global driver

    if not driver:
        driverEnv = get_driverEnv(**args)
        driver = driverEnv.get_driver()
    return driver

def get_static_setup(**opt):
    verbose = opt.get('verbose', 0)

    env = tpsup.envtools.Env()
    env.adapt()
    static_setup = {}
    if env.isWindows:
        static_browser_path = f"{os.environ['SITEBASE']}/{env.system}/{env.os_major}.{env.os_minor}/Chrome/Application/chrome.exe"
        static_driver_path = f"{os.environ['SITEBASE']}/{env.system}/{env.os_major}.{env.os_minor}/chromedriver/chromedriver.exe"
        
        # convert to native path: for windows, we convert it to batch path with forward slash for cygwin/gitbash/powershell
        static_browser_path = tpsup.envtools.convert_path(static_browser_path, target_type='batch')
        static_driver_path = tpsup.envtools.convert_path(static_driver_path, target_type='batch')
        if verbose:
            print(f"get_static_setup: converted: static_browser_path={static_browser_path}")
            print(f"get_static_setup: converted: static_driver_path={static_driver_path}")
    elif env.isLinux:
        # static_browser_path = f"{os.environ['SITEBASE']}/{env.system}/{env.os_major}.{env.os_minor}/Chrome/Application/chrome"
        tatic_browser_path = f"/usr/bin/google-chrome"
        static_driver_path = f"{os.environ['SITEBASE']}/{env.system}/{env.os_major}.{env.os_minor}/chromedriver/chromedriver"
    elif env.isMac:
        # static_browser_path = f"{os.environ['SITEBASE']}/{env.system}/{env.os_major}.{env.os_minor}/Google Chrome.app/Contents/MacOS/Google Chrome"
        static_browser_path = f"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        static_driver_path = f"{os.environ['SITEBASE']}/{env.system}/{env.os_major}.{env.os_minor}/chromedriver/chromedriver"
    else:
        raise RuntimeError(f"unsupported system={env.system}")
    if verbose:
        print(f"get_static_setup: static_browser_path={static_browser_path}")

    static_setup['chrome'] = static_browser_path
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
    print(f"check_setup: expected static_setup={pformat(static_setup)}")

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
                chrome_vesion = run_cmd_clean(f'''chrome_version "{found_path['chrome']}"''', is_bash=True)
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
        self.debug = opt.get('debug', 0)

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
            # 2025/01/01, we can separate the click logic from the find logic now.
            #     so 'click_xpath' can be done as 'xpath' and 'click' in two separate steps.
            #     'click_xpath' was introduced in 2021 for the old locator+action style of flow.
            #      now our new flow is locator+locator+...
            #     'click_xpath' is still supported for backward compatibility and reminder of 
            #     caveat of the difference between found element vs active element.
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


class tp_find_element_by_chains:
    # check whether one of the chains matches any element
    def __init__(self, chains2: list, **opt):
        self.opt = opt
        self.debug = opt.get('debug', 0)
        self.matched_so_far = [] # this saves the matched path so far, for debugging purpose.

        # print(f"tp_find_element_by_chains: chains2={pformat(chains2)}")

        self.chains = []
        for chain in chains2:
            self.matched_so_far.append([])
            # self.matched_numbers.append([])
            self.chains.append([])

        # print(f"tp_find_element_by_chains: self.chains={pformat(self.chains)}")
        
        # parse user specified 'chains2' and save it in 'self.chains'
        #    we parse it in _init__ so that we don't have to parse it in __call__ every time.
        #
        # example: convert ONE chain (from user specified 'chains2')
        # from 
        #   [
        #     'xpath=/html/body[1]/ntp-app[1]', 
        #     'shadow', 
        #     'css=#mostVisited',
        #     'shadow',
        #     'css=#removeButton2,css=#actionMenuButton',
        #   ],
        # into ONE chain in 'self.chains'.
        #   [
        #     [['xpath', '/html/body[1]/ntp-app[1]']],
        #     [['shadow']], 
        #     [['css', '#mostVisited']], 
        #     [['shadow']] ,
        #     [['css', '#removeButton2'], ['css', '#actionMenuButton']], # this is the reason we need extra brackets.
        #   ]
        for i in range(0, len(chains2)):
            chain = chains2[i]
            for locator in chain:
                print(f"locator={locator}")
                if (locator == "shadow") or (locator == "iframe"):
                    self.chains[i].append([[locator]])
                elif m1 := get_locator_compiled_path1().match(locator):
                    # locator => path_type, path_string_and extra
                    # 'xpath=/html/body[1]/ntp-app[1]' => ['xpath', '/html/body[1]/ntp-app[1]']
                    # 'css=#removeButton2,css=#actionMenuButton' => ['css', '#removeButton2,css=#actionMenuButton']                                 
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
        
        if self.debug:
            print(f'parsed chains = {pformat(self.chains)}')

        for chain_idx in range(0, len(self.chains)):
            # make sure we start from the same domstack every time.
            if self.debug:
                print("replay domstack")
            replay_domstack(domstack)

            local_domstack = domstack.copy()    

            chain = self.chains[chain_idx]
            if self.debug:
                print(f'testing chain = {pformat(chain)}')

            locator_driver = driver
            self.matched_so_far[chain_idx].clear()

            found_chain = True

            for locator_idx in range(0, len(chain)):
                locator= chain[locator_idx]
                if self.debug:
                    print(f'testing locator = {pformat(locator)}')
                if locator[0][0] == "shadow":
                    try:
                        locator_driver = e.shadow_root  # shadow_driver is a webdriver type
                        self.matched_so_far[chain_idx].append(locator[0][0])

                        if self.debug:
                            print(f"found {locator[0][0]}")
                    except Exception as ex:
                        if self.debug:
                            print(f"not found {locator[0][0]}")
                        found_chain = False
                        break

                    # update local_domstack
                    url = get_shadowHost_info(e)
                    local_domstack.append({
                        'type': 'shadow',
                        'element': e,
                        'url': url,
                    })
                elif locator[0][0] == "iframe":
                    # update local_domstack before we switch to iframe
                    url = e.get_attribute('src') # this is child (future) iframe's url
                    if not url:
                        url = 'about:srcdoc'
                    local_domstack.append({
                        'type': 'iframe',
                        'element': e,
                        # we need to save url before we switch into iframe.
                        # otherwise, if we need url later, we would have to switch back to this iframe.
                        'url': url,
                    })
                    try:
                        driver.switch_to.frame(e)
                        locator_driver = driver
                        self.matched_so_far[chain_idx].append(locator[0][0])
                        if self.debug:
                            print(f"found {locator[0][0]}")
                    except Exception as ex:
                        if self.debug:
                            print(f"not found {locator[0][0]}")
                        found_chain = False
                        break
                else:
                    type_paths = locator
                    if self.debug:
                        print(f"type_paths = {pformat(type_paths)}")

                    one_parallel_path_matched = False
                    for type_path in type_paths:
                        ptype, path = type_path # path_type and path
                        if self.debug:
                            print(f'testing {ptype}={path}')
                        if "xpath" in ptype:  # python's string.contains() method
                            try:
                                e = locator_driver.find_element(By.XPATH, path)
                            except Exception:
                                # j += 1
                                if self.debug:
                                    print(f"not found xpath {ptype}={path}")
                                continue
                        elif "css" in ptype:
                            try:
                                e = locator_driver.find_element(
                                    By.CSS_SELECTOR, path)
                            except Exception:
                                # j += 1
                                if self.debug:
                                    print(f"not found css {ptype}={path}")
                                continue
                        else:
                            raise RuntimeError(
                                f"unsupported path type={ptype}")

                        self.matched_so_far[chain_idx].append(f"{ptype}={path}")
                        if self.debug:
                            print(f'found {ptype}="{path}"')
                        one_parallel_path_matched = True
                        break
                    if self.debug:
                        print(
                            f'one_parallel_path_matched={one_parallel_path_matched}')
                    if not one_parallel_path_matched:
                        found_chain = False
                        if self.debug:
                            print(f"matched so far = {pformat(self.matched_so_far[chain_idx])}")
                        break

                if not e:
                    # some locators don't explicitly return an element, therefore, we set it here.
                    e = driver.switch_to.active_element
                    if not e:
                        raise RuntimeError(f'cannot find active element')
                self.current_matched_path = self.matched_so_far[chain_idx].copy

            if found_chain:
                # e.tpdata = {"ptype" : ptype, "path" : path, "position" : i}

                e.tpdata = {
                    "position": chain_idx,
                    "domstack": local_domstack,
                }  # monkey patch for convenience

                return e
        return None


def tp_get_url(url: str, **opt):
    global driver
    global domstack
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
    
    # clear global domstack
    domstack.clear()

def correct_xpath(path: str) -> str:
    '''
    in windows gitbash, xpath=/html/body[1] will be converted to xpath=C:/Program Files/Git/html/body[1].
    we need to correct it to xpath=/html/body[1]
    '''
    new_path = re.sub(r'xpath=C:/Program Files/Git', 'xpath=', path, re.IGNORECASE, re.DOTALL)
    if path != new_path:
        print(f"corrected xpath: {path} => {new_path}")

    return new_path

# we will use the following patterns more than once, therefore,
# we centralize them into functions, so we can easily change their behavior
def get_locator_compiled_path1():
    return re.compile(r"\s*(?<!gone_)(xpath|css|click_xpath|click_css)=(.+)",
                      re.MULTILINE | re.DOTALL)

def get_locator_compiled_path2():
    return re.compile(
        r"(.+?)(?:\n|\r\n|\s?)*,(?:\n|\r\n|\s?)*(xpath|css|click_xpath|click_css)=",
        re.MULTILINE | re.DOTALL)

dump_readme = '''

the dump() function aims to dump everything that you can find in chrome devtools source tab.

element/
    directory for dumping the current element

iframe/
    directory for dumping the current (or closest) iframe that contains the element.
    there could be shadow doms between the element and the iframe.

shadow/
    directory for dumping the currnet (or closest) shadow dom that contains the element.
    there could be iframes between the element and the shadow dom.

page/
    directory for dumping the whole page

iframe*.html
    the iframe html of the page (dump all) or specified element (dump element)
    note that when there is a shadow dom, the iframe*.html doesn't show the shadow dom's content;
    you need to look at shadow*.html for that.

locator_chain_list.txt
    the locator chain on command line format
    eg
        "xpath=id('shadow_host')" "shadow"
        "xpath=id('shadow_host')" "shadow" "css=#nested_shadow_host" "shadow"

locator_chain_map.txt
    The most useful file!!!

    the locator chain to shadow/iframe mapping. 
    This shows how to reach to each child shadow or iframe from the scope (element, iframe, or root).
    you can run ptslnm with the chain on command line to locate the element.
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
screenshot_iframe.png
screenshot_shadowhost.png
screenshot_page.png
    the screenshot of the element, iframe, shadow, or the whole page.

shadow*.html
    the shadow dom of the page or specific element.
    it is the HTML of the shadow host.

source_element.html
source_iframe.html
source_shadowhost.html
source_page.html
    the source html specific to dump scope: element, iframe, shadow, or page.

    note that when there is a child iframe/shadow dom, the source*.html doesn't show 
    the child iframe/shadow dom's full content.
    The content of the child's iframe and shadow dom can be found in iframe*.html 
    and shadow*.html of that child.

    source.html will be different from the original html also because source.html contains
    dynamic content, such as js generated content.

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
            $ ptslnm url=newtab dump_all=$HOME/dumpdir
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
            $ ptslnm url=newtab -locator "xpath=/html[@class='focus-outline-visible']/body[1]/ntp-app[1]" "shadow" "css=#searchbox"
    
'''

def dump(output_dir: str, scope: str = 'element',  **opt):
    global driver
    global locator_driver
    global domstack
    global last_element
    
    debug = opt.get('debug', 0)
    verbose = opt.get('verbose', debug)

    '''
    about the scope:
        element: dump the last element's info
        iframe:  dump everything about the innest iframe dom covering element.
        shadow:  dump everything about the innest shadowHost covering element.
        page:    dump the whole page.
        all:     dump all scopes: 'element', 'dom', 'page', into separate subdirs.

        for example,
        ptslnm -rm -debug "file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html" -dump="C:/Users/tian/dumpdir2" xpath=//iframe[1] iframe "xpath=//body/p"
        the chain is: xpath=//iframe[1] iframe "xpath=//body/p"

        if appending "-scope element", we dump the last element, which is the <p> element. 
            source_elemnet.html only contains the <p> element.
        if appending "-scope shadow",  we dump the closest shadowHost of the <p> element.
            we cannot dump shadowRoot because shadowRoot is stripped-down version of WebDriver, which
            doesn't have page_source attribute ...
        if appending "-scope iframe,  we dump the closest iframe of the <p> element.
        if appending "-scope page",   we dump the whole page.
        if appending "-scope all",    we dump all scopes: element, shadow, iframe, page.
    '''

    # output_dir can be from both **opt and step, to avoid the multiple-values error,
    # we group output_dir into **opt, allowing override kwargs

    # save a copy of README.txt
    readme_file = f"{output_dir}/README.txt"

    os.makedirs(output_dir, exist_ok=True)  # this is mkdir -p

    with open(readme_file, "w", encoding="utf-8") as readme_fh:
        readme_fh.write(dump_readme)
        readme_fh.close()
    
    start_node = None
    if scope == 'element' or scope == 'all':
        subdir = f"{output_dir}/element"
        os.makedirs(subdir, exist_ok=True)  # this is mkdir -p
        print()
        print(f"locate: dump element to {subdir}")

        # element = driver.switch_to.active_element
        # if element is None:
        if last_element:
            source_file = f"{subdir}/source_element.html"
            screenshot_file = f"{subdir}/screenshot_element.png"
            with open(source_file, "w", encoding="utf-8") as source_fh:
                source_fh.write(last_element.get_attribute('outerHTML'))
                # screenshot the element
                # element.click()
            last_element.screenshot(screenshot_file)

            dump_deeper(subdir, element=last_element, **opt)
        elif scope == 'element':
            raise RuntimeError(f"scope is element, but last_element is not set")
    if scope == 'shadow' or scope == 'all':
        subdir = f"{output_dir}/shadow"
        os.makedirs(subdir, exist_ok=True)  # this is mkdir -p
        print()
        print(f"locate: dump shadow to {subdir}")

        # dump shadow host if the element is in a shadow dom,  eg, shadow, or iframe.shadow.
        # but shadow.iframe doesn't count.
        source_file = f"{subdir}/source_shadowhost.html"
        screenshot_file = f"{subdir}/screenshot_shadowhost.png"

        # shadowHost = js_get(element, "shadowhost") # this gives the immediate shadow host of the element
        # eg, shadow, or iframe.shadow. but shadow.iframe doesn't count.

        # we can also get shadow host from domstack. if there is a iframe in between, we still dump 
        # the shadow host.
        result = get_domstack('last_shadow')
        if result:
            shadowHost = result['item']['element']
            domstack2 = result['domstack']

            # remove the last shadow from domstack2, in order to access the shadow host
            domstack2.pop()

            # play domstack2
            # this doesn't change global domstack.
            replay_domstack(domstack2) 

            # dump shadow host
            with open(source_file, "w", encoding="utf-8") as source_fh:
                source_fh.write(shadowHost.get_attribute('outerHTML'))
            shadowHost.screenshot(screenshot_file)

            # now we are done with investigating the shadow host, we can dump the shadow content.
            # first, restore domstack
            replay_domstack(domstack)

            dump_deeper(subdir, element=None, scope='shadow', **opt)
        elif scope == "all":
            print(f"scope is all, but no shadow host found")
        else:
            raise RuntimeError(f"scope is shadow, but no shadow host found")
    if scope == 'iframe' or scope == 'all':
        subdir = f"{output_dir}/iframe"
        os.makedirs(subdir, exist_ok=True)  # this is mkdir -p
        print()
        print(f"locate: dump iframe to {subdir}")

        source_file = f"{subdir}/source_iframe.html"
        screenshot_file = f"{subdir}/screenshot_iframe.png"

        with open(source_file, "w", encoding="utf-8") as source_fh:  
            '''
            driver.page_source may not be the whole page.
                - If driver is in iframe, driver.page_source will only show
                  the content of the iframe. (dump_scope=iframe)
                - If we are in an iframe and wanted to see the whole page, we
                  need to go out of all iframes using driver.switch_to.default_content()
                - if driver is not in any iframe, driver.page_source will show
                  the whole page. (dump_scope=page)
                - if driver enters shadowRoot, shadowRoot doesn't have page_source,
                  therefore, we can only use driver.page_source to get the shadow's
                  parent iframe's source.
                - driver.page_source will not show the content of the iframe or shadow inside it.        
            '''
            source_fh.write(driver.page_source)

        # to dump screenshot, we need to see the element. 
        # iframe's element cannot be seen from the iframe dom, we need to go to the parent frame.
        # this situation is same to shadowRoot.
        result = get_domstack('last_iframe')
        if result:
            iframeelement = result['item']['element']
            domstack2 = result['domstack']

            # two ways to go to the parent frame
            # way-1: like we did with shadow
            # # remove the last iframe from domstack2
            # domstack2.pop()
            # # play domstack2
            # replay_domstack(domstack2)

            # way-2:
            # go to parent frame
            driver.switch_to.parent_frame()

            # screenshot the iframe
            iframeelement.screenshot(screenshot_file)

            # restore driver state but no need to restore domstack because we never changed it
            replay_domstack(domstack)

            dump_deeper(subdir, element=None, **opt)
    if scope == 'page' or scope == 'all':
        subdir = f"{output_dir}/page"
        os.makedirs(subdir, exist_ok=True)  # this is mkdir -p
        print()
        print(f"locate: dump page to {subdir}")
        
        source_file = f"{subdir}/source_page.html"
        screenshot_file = f"{subdir}/screenshot_page.png"

        # 1. save current domstack
        domstack_save = domstack.copy()

        # 2. switch to top - clear domstack
        driver.switch_to.default_content()
        domstack.clear()
        locator_driver = driver
        driver_url = driver.current_url

        # save the whole page's screenshot
        driver.save_screenshot(screenshot_file)

        # 3. dump - dump() will not change domstack
        dump_deeper(subdir, element=None, **opt)

        # 4. restore driver dom and domstack
        replay_domstack(domstack_save)
        domstack = domstack_save

        

def dump_deeper(output_dir: str, element: WebElement = None, scope:str=None, **opt):
    # prepare for recursive dump
    if element:
        iframe_list = element.find_elements(By.XPATH, './/iframe')
    elif scope and scope == 'shadow':
        print(f"locator_driver={locator_driver}")
        # iframe_list = locator_driver.find_elements(By.XPATH, './/iframe')
        # this gives error: "Message: invalid argument: invalid locator"
        # because xpath doesn't work under shadow dom.
        # under shadow dom, we have to use CSS_SELECTOR.
        iframe_list = locator_driver.find_elements(By.CSS_SELECTOR, 'iframe')
        print(f"iframe_list={iframe_list}")
    else:
        iframe_list = driver.find_elements(By.XPATH, '//iframe')

    dump_state = {
        'output_dir': output_dir,

        'type_chain': [],  # iframe, shadow, ... to current iframe/shadow
        'typekey_chain': [],  # iframe001, shadow001 ... to current iframe/shadow
        'locator_chain': [],  # 'xpath=/a/b', 'shadow', 'css=div' ... to current iframe/shadow
        'xpath_chain': [],  # /a/b, shadow, /div ... to current iframe/shadow

        # performance stats
        'scan_count': {
            'iframe': 0,
            'shadow': 0,
        },
        'exist_count': {
            'iframe': 0,
            'shadow': 0,
        },
        'max_depth_so_far': 0,

        # file handlers - will be opened below
        # 'list': {
        #     'locator_chain': None,
        #     'xpath_chain': None,
        #     'xpath': None,
        # },
        # 'map': {
        #     'locator_chain': None,
        #     'xpath_chain': None,
        #     'xpath': None,
        # },
    }

    for format in ['list', 'map']:
        dump_state[format] = {}
        for scheme in ['locator_chain', 'xpath_chain', 'xpath']:
            f = f"{output_dir}/{scheme}_{format}.txt"
            dump_state[format][scheme] = open(f, "w", encoding="utf-8")

    for iframe in iframe_list:
        dump_recursively(iframe, dump_state, 'iframe', **opt)

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

    # unlike iframe are always under iframe tag, shadow host can be any tag, 
    # therefore, we need to try every element. 
    # if element.shadow_root exists, it is a shadow host.
    # note: under shadow dom, XPATH doesn't work, you would get error:
    #   "Message: invalid argument: invalid locator"
    # xpath works under element and iframe but for consistency, we use CSS_SELECTOR everywhere.
    if element:
        start_node = element
        find_css = '*'
        dump_recursively(element, dump_state, 'shadow', **opt)  
    elif scope and scope == 'shadow':
        start_node = locator_driver
        find_css = '*'
    else:
        start_node = driver
        find_css = '*'    

    for e in start_node.find_elements(By.CSS_SELECTOR, find_css):
        dump_recursively(e, dump_state, 'shadow', **opt)

    # close all file handlers after we finish
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

    # we put the chain check at last so that summary will be printed before the program exits.
    if scan_depth != 0:
        # when we exit, the chain should be empty
        raise RuntimeError(f"dump_state type_chain is not empty")


def dump_recursively(element: WebElement, dump_state: dict, type: str, **opt):
    debug = opt.get('debug', 0)

    dump_state['scan_count'][type] += 1 # type is iframe or shadow

    # begin performance stats
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
            if debug > 1:
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
    except NoSuchElementException as e:
        print(e)
        print_domstack()
        print_iframestack()
        exit(1)

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

    # update locator chains to current iframe/shadow
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

    # save the current iframe/shadow's chains to files
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
        # diagarm: parent iframe -> element (child iframe) -> grandchild iframe/shadow.
        # we need to 
        #   1. go into the element (child iframe) content (context)
        #   2. dump the child iframe content
        #   3. recursively dump the grandchild iframes and shadows
        #   4. go back up 1 level, to the parent iframe content (context) - ie, get out of the child iframe
        # this part we don't update domstack because the dom switch is predictable and restored at the end.

        # 1. go into the iframe content (context)
        driver.switch_to.frame(element)
        # tp_switch_to_frame(element)

        # 2. dump the iframe content
        with open(output_file, "w", encoding="utf-8") as ofh:
            ofh.write(driver.page_source)
            ofh.close()

        # 3. recursively dump the child iframes and shadows
        # 3.1 find sub iframes in this frame
        iframe_list = driver.find_elements(By.XPATH, '//iframe')
        for sub_frame in iframe_list:
            dump_recursively(sub_frame, dump_state, 'iframe', **opt)

        # 3.2 find shadows in this frame
        for e in driver.find_elements(By.XPATH, "//*"):
            dump_recursively(e, dump_state, 'shadow', **opt)

        # 4. go back up 1 level, to the parent iframe content (context) - ie, get out of the child iframe
        driver.switch_to.parent_frame()
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
            dump_recursively(iframe, dump_state, 'iframe', **opt)

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

            # e may or may not be a shadow host. 
            # dump_recursively will figure it out whether it is a shadow host or not.
            dump_recursively(e, dump_state, 'shadow', **opt)

    # restore the locator chains to the previous iframe/shadow
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
          'var' can be used multiple times for the same variable; the second declaration does
           not create new variable,;it will be ignored.
        - "const" is block scoped, like "let". 
    '''

    # in_shadowDom vs shadowHost:
    #     in_shadowDom is a python var used for js to keep track of whether we are in shadow dom or not.
    #     shadowHost is a js var used to return to python so that python can update locator_driver.
    in_shadowDom = False

    # if shadowHost is not null, we need to update locator_driver to shadowHost.shadowRoot.
    js_start = '''
var shadowHosts = []; // we assume we start from outside of shadow dom. shawdowHosts is an array.
var iframeElement = null; // we assume we start from outside of iframe. 
var startDoc = document;
if (window.iframeDoc) {
    startDoc = window.iframeDoc;
}
var e = startDoc'''

    js = js_start
    for locator in locator_chain:
        if m := get_locator_compiled_path1().match(locator):
            # we can only convert single path, eg, xpath=/a/b
            # we cannot conver multiple path, eg, xpath=/a/b,xpath=/c/d
            ptype, path = m.groups()
            if ptype == 'xpath':
                if not in_shadowDom:
                    js += f'.evaluate("{path}", startDoc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue'
                else:
                    raise RuntimeError("xpath is not supported in shadow dom. use css instead")
            elif ptype == 'css':
                js += f'.querySelector("{path}")'
            else:
                raise RuntimeError(
                    f"unsupported ptype={ptype} in locator={locator}")
        elif locator == 'shadow':
            # change shadowHost. this tells python to change locator_driver to shadow driver.
            # once we enter shadow dom, we reset iframeDoc/iframeElement to null.
            # because shaodowRoot doesn't need change document, therefore, we don't need
            # using 'window' to persist shadowHost, we can pass shadowHost to caller (python).
            js += '; window.iframeDoc = null; window.iframeElement = null; shadowHosts.push(e); e = e.shadowRoot' 
            # js += '.shadowRoot' 
            in_shadowDom = True    
        elif locator == 'iframe':
            """
            this is comment.
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

            what is: let iframe_inner = e.contentDocument || e.contentWindow.document;

            https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#scripting
            
            With the DOM HTMLIFrameElement object, scripts can access the window object of 
            the framed resource via the contentWindow property. The contentDocument property
            refers to the document inside the <iframe>, same as contentWindow.document.

            From the inside of a frame, a script can get a reference to its parent window with
            window.parent.

            Script access to a frame's content is subject to the same-origin policy. 
            Scripts cannot access most properties in other window objects if the script
            was loaded from a different origin...
            """
            js +=''';
var iframeElement = e;
// enter iframe. this can trigger the 'null origin' error when we run with file url without --all-file-access.
window.iframeDoc = e.contentDocument || e.contentWindow.document; 

// we cannot return any element once we entered iframe because we would get error: 
//      stale element not found in the current frame"
// so instead of returning element, we return indicator (int), and persist iframeDoc and iframeElement
// in global variable 'window'.
window.iframeElement = e;

// we return 1 to indicate the variable is set.
// return { 'iframeElementIsSet': 1 }; 
return { 'iframeElement': iframeElement, 'shadowHosts': shadowHosts };
'''
# we used to use below code to run with file url before we have --all-file-access.
# the main draw back is that it does not allow us to go back to parent iframe.
# ie, it makes driver.switch_to.default_content() to not go back to the top.
#             js += ''';
# // remove shadowHost because iframe is not in shadow dom, no need to change locator_driver.
# var shadowHost = null;
# try {
#     // cd(e.contentWindow); // cd is not defined in chrome's js. it is only in firefox.
#     // let iframe_inner = e.contentDocument || e.contentWindow.document;
#     window.iframeDoc = e.contentDocument || e.contentWindow.document; // enter iframe. this can trigger the error to catch below.
#     const current_origin = window.location.origin;
#     console.log(`iframe stays in the same origin ${current_origin}`); // note to use backticks
# } catch(err) {
#     // print the error. note that console.log() is not available in Selenium. 
#     // console log is only available in browser's webtools console.
#     // we have a locator 'consolelog' to print it out. 
#     console.log(err.stack);
#     let iframe_src = e.getAttribute('src');
#     iframe_url = new URL(iframe_src);
#     iframe_url = iframe_src;
#     console.log(`iframe needs new url ${iframe_url}`);  // note to use backticks
#     // window is the main JavaScript object root. 
#     // window.document or just document is the main object of the potentially visible.
#     // below replaces the whole object root - then we loss all the previous objects, eg, iframe parent.
#     // basically we start a new page with the iframe's url.
#     window.location.replace(iframe_url);
# }
#             '''

            # save one js after every iframe because document is reset to iframe's document.
            # and this iframe js doesn't change locator_driver because only shadow dom changes locator_driver.
            # so every 'iframe' creates a new js. 
            # the next js will run with a new document (iframe's document).
            if trap:
                js = wrap_js_in_trap(js)
            js_list.append(js)

            # start another js 
            # js = 'var shadowHost = null; var e = document'
            js = js_start

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
    if js == js_start:
        # if js is still the same as js_start, we don't need to append it.
        pass
    else:
        if js.endswith('.shadowRoot'):
            js = js[:-len('.shadowRoot')]

        # save the last js.
        #   - only the last js 'return e'
        #   - the intermediate js were all ending with iframes
        # js += ';\nreturn {element: e, shadowHost: shadowHost};\n'
        js += ';\nconsole.log(`e=${e}, shadowHosts=${shadowHosts}`);\nreturn {"element": e, "shadowHosts": shadowHosts};\n'
        # js += ';\nreturn e;\n'
        # js += ';\nreturn [1, 2];\n'
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
                locator = correct_xpath(locator)
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
    # get current parent shadowRoot's shadowHost
    'shadowhost': '''
        var root = arguments[0].getRootNode();
        if (root.nodeType === Node.DOCUMENT_FRAGMENT_NODE && root.host != undefined) {
            return root.host;
        } else {
            return null;
        }
    ''',
    # get the current iframe's iframeElement (if any) of the current context
    # javascript can get current iframe's document object too, which is
    #    window.iframeDoc = e.contentDocument || e.contentWindow.document;
    # but javascript cannot return it back to python's 
    #    driver.execute_script("return window.iframeDoc")
    # because the document object is not serializable. 
    # Only element and primitive types are serializable.
    'iframeelement': '''
        if (window.self !== window.top) {
            // You are in an iframe
            return window.frameElement; 
        } else {
            // Not in an iframe
            return null;
        }
    ''',

    # get the current iframe's and its parent iframes' iframeElement and URL.
    # we can get their iframe document too, but we cannot return it back to python
    # because the document object is not serializable.
    #
    # I couldn't add the iframeElement to the return value because I got the following error:
    #     selenium.common.exceptions.JavascriptException: Message: javascript error: 
    #        {"status":10,"value":"stale element not found in the current frame"}
    # when I ran
    #     ptslnm url="http://localhost:8000/iframe_nested_test_main.html" sleep=1 
    #         debug_after=url,consolelog,domstack,iframestack "xpath=//iframe[1]" 
    #         "iframe" "xpath=//iframe[2]" "iframe" "xpath=//iframe[1]" "iframe" 
    #         "xpath=/html/body/div[1]/p[1]" 

    'iframestack': '''
        var iframes = []; // each element is a dict with 'element' and 'url'

        // push current iframe's element and url
        url = window.location.href;
        iframes.push(
            { 
                //'element': window.parent.frameElement, 
                'url': url 
            }
        );

        var current = window;
        
        while (current.self !== window.top) {
            current = current.parent;

            if (!current) {
                break;
            }
            
            if (!current.frameElement) {
                // we are at the top
                url = current.location.href;
                iframes.push({ 'url': url});
                break;
            }   
            url = current.frameElement.contentWindow.location.href;
            iframes.push(
                { 
                    // 'element': current.frameElement,
                    'url': url
                }
            );

            
        }

        return iframes;
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

    # driverEnv = SeleniumEnv("localhost:19999", debug=1)
    driverEnv = SeleniumEnv("auto", debug=0)
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
    # cmd_term = tpsup.envtools.get_term_type()
    # if cmd_term == 'batch':
    #     # list all the log files for debug purpose
    #     # use double quotes to close "C:/Users/.../selenium*" because bare / is a switch in cmd.exe.
    #     dir = f'"{driverEnv.log_base}/"seleninum*'
    # else:
    #     dir = f'{driverEnv.log_base}/seleninum*'.replace('\\', '/')
    # cmd = f"{my_env.ls_cmd} -ld {dir}"

    # list all the log files for debug purpose
    # use double quotes to close "C:/Users/.../selenium*" because bare / is a switch in cmd.exe.
    cmd = f"{my_env.ls_cmd} -ld \"{driverEnv.log_base}/\"seleninum*"
    
    print(f"cmd = {cmd}")
    os.system(cmd)

def helper_find_element(path:str):
    """
    helper function to find an element by path.
    This is used by locate() and locate_dict() to find an element.
    """
    global driver
    global locator_driver
    global last_element
    global domstack
    global debuggers

    if not driver:
        print("driver is not set. Please set driver first.")
        return

    if not path:
        print("path is empty. Please provide a valid path.")
        return

    # we use locator_driver to find the element, so that we can switch to shadow dom if needed.
    if not locator_driver:
        print("locator_driver is not set. Using driver as locator_driver.")
        return
    
    if m := re.match(r'css=(.*)', path):
        # if path starts with css=, we use css selector to find the element.
        path = m.group(1)
        # we use css selector to find the element.
        # this is the same as driver.find_element(By.CSS_SELECTOR, path)
        print(f"Using css selector to find element: {path}")
        try:
            locator_driver.find_element(By.CSS_SELECTOR, path)
            print(f"Found element by css selector: {path}")
        except Exception as e:
            print(f"{e}")
            return None
    elif m := re.match(r'xpath=(.*)', path):
        # if path starts with xpath=, we use xpath to find the element.
        path = m.group(1)
        # we use xpath to find the element.
        # this is the same as driver.find_element(By.XPATH, path)
        print (f"Using xpath to find element: {path}")
        try:
            locator_driver.find_element(By.XPATH, path)
            print(f"Found element by xpath: {path}")
        except Exception as e:
            print(f"{e}")
            return None
    else:
        print(f"Unsupported path format: {path}. Please use css= or xpath= prefix.")
        return None

helper = {
    'de': {
        'desc': 'dump_element',
        'func': dump,
        'args': {
            'scope': 'element',
            'output_dir': tpsup.tmptools.tptmp().get_nowdir(mkdir_now=0),
            # we delay mkdir, till we really need it
        },
        'usage': f'''
        dump the current element. no arg. output to
        {tpsup.tmptools.tptmp().get_nowdir(mkdir_now=0)}
        ''',
    },

    'dp': {
        'desc': 'dump_page',
        'func': dump,
        'args': {
            'scope': 'page',
            'output_dir': tpsup.tmptools.tptmp().get_nowdir(mkdir_now=0),
            # we delay mkdir, till we really need it
        },
        'usage': f'''
        dump the current page. no arg. output to
        {tpsup.tmptools.tptmp().get_nowdir(mkdir_now=0)}
        ''',
    },

    'df': {
        'desc': 'dump_iframe',
        'func': dump,
        'args': {
            'scope': 'iframe',
            'output_dir': tpsup.tmptools.tptmp().get_nowdir(mkdir_now=0),
            # we delay mkdir, till we really need it
        },
        'usage': f'''
        dump the current page. no arg. output to
        {tpsup.tmptools.tptmp().get_nowdir(mkdir_now=0)}
        ''',
    },

    'ds': {
        'desc': 'dump_page',
        'func': dump,
        'args': {
            'scope': 'shadow',
            'output_dir': tpsup.tmptools.tptmp().get_nowdir(mkdir_now=0),
            # we delay mkdir, till we really need it
        },
        'usage': f'''
        dump the current shadow DOM. no arg. output to
        {tpsup.tmptools.tptmp().get_nowdir(mkdir_now=0)}
        ''',
    },

    'p': {
        'desc': 'find element by path',
        'func': helper_find_element,
        'args': {
            'fromUser': True
        },
        'usage': '''
        test find_element path: xpath or css. Examples
        p css=#my_element_id
        p xpath=/a/b
        ''',
    },
}

def locate_dict(step: dict, **opt):
    dryrun = opt.get("dryrun", 0)
    interactive = opt.get("interactive", 0)
    debug = opt.get("debug", 0)
    dryrun = opt.get("dryrun", 0)
    
    global driver
    global driver_url
    global locator_driver
    global last_element
    global domstack
    global debuggers
    
    if debug:
        print(f"locate_dict: step={pformat(step)}")

    # helper = {}  # interactivity helper
    # if interactive:
    #     helper = {
    #         'd': {
    #             'desc': 'dump_page',
    #             'func': dump,
    #             'args': {
    #                 'driver': driver,
    #                 'output_dir': tpsup.tmptools.tptmp().get_nowdir(mkdir_now=0)
    #                 # we delay mkdir, till we really need it
    #             }
    #         },
    #         'p': {
    #             'desc': 'find element by path',
    #             'func': helper_find_element,
    #             'args': {
    #                 'fromUser': True
    #             },
    #         },
    #     }

    ret = {'Success': False, 'break_levels': 0, 'continue_levels': 0}

    locator_type = step.get('type', None)
    action = step.get('action', None)

    if locator_type == 'simple':
        # locator must be a string
        locator = step.get('locator', None)
        if type(locator) != str:
            raise RuntimeError(f"simple step locator must be a string, but got {type(locator)}, step={pformat(step)}")
        
        if dryrun:
            # syntax check only. therefore we don't check the return value.
            locate(locator, **opt)

            for status in ['Success', 'Failure']:
                if status in step:
                    locate(step[status], **opt)
            return ret
        
        result = locate(locator, **opt)

        if debug:
            print(f"locate_dict: result={pformat(result)}")

        # always check 'break_levels' first before checking 'Success'
        if result['break_levels']:
            ret['break_levels'] = result['break_levels']
            # break now, by returning ret
            return ret
        
        if result['continue_levels']:
            ret['continue_levels'] = result['continue_levels']
            # continue now, by returning ret
            return ret

        if result['Success']:
            # we found the element
            if 'Success' in step:
                result2 = locate(step['Success'], **opt) # we don't use follow() here, because we don't want to be recursive.

                if result2['break_levels']:
                    ret['break_levels'] = result2['break_levels']
                    return ret
                if result2['continue_levels']:
                    ret['continue_levels'] = result2['continue_levels']
                    return ret
            ret['Success'] = result2['Success']
        else:
            # we didn't find the element
            if 'Failure' in step:
                result2 = locate(step['Failure'], **opt)
                if result2['break_levels']:
                    ret['break_levels'] = result2['break_levels']
                    return ret
                if result2['continue_levels']:
                    ret['continue_levels'] = result2['continue_levels']
                    return ret
                ret['Success'] = result2['Success']
            else:
                raise RuntimeError(f"locator failed. step={pformat(step)}")
    elif locator_type == 'parallel':
        # paths must be a list
        paths = action.get('paths', None)
        if type(paths) != list:
            raise RuntimeError(f"parallel step paths must be a list, but got {type(paths)}, step={pformat(step)}")

        if dryrun:
            # dryrun is to check syntax only. therefore we don't check the return value.
            for path in paths:
                locator = path.get('locator', None)
                if type(locator) != str:
                    raise RuntimeError(f"'parallel' step 'locator' must be a string, but got {type(locator)}, step={pformat(step)}")
                locate(locator, **opt)
                if 'Success' in path:
                    locate(path['Success'], **opt)
                if 'Failure' in path:
                    locate(path['Failure'], **opt)
            if 'Success' in action:
                locate(action['Success'], **opt)
            if 'Failure' in action:
                locate(action['Failure'], **opt)
            return ret
        
        # concatenate all paths' locators into a single string so that we can call locate()
        # which take a string of locators, separated by comma.
        # locate() calls tp_find_element_by_paths() which can take multiple locators in parallel.
        locators_string = ",".join([path['locator'] for path in paths])

        result = locate(locators_string, **opt)

        # copy result to ret
        ret['Success'] = result['Success']
        
        # always check 'break_levels' first before checking 'Success', because when 'break_levels' is set,
        # we don't care about 'Success'.
        if result['break_levels']:
            ret['break_levels'] = result['break_levels']
            return ret
        if result['continue_levels']:
            ret['continue_levels'] = result['continue_levels']
            return ret

        if result['Success']:
            # we found the element, the corresponing locator is in result['element'].tpdata
            tpdata = getattr(last_element, 'tpdata', None)
            path_index = tpdata['position']

            path = paths[path_index]
            if 'Success' in path:
                # path-level Found
                result2 = locate(path['Success'], **opt)
                if result2['break_levels']:
                    ret['break_levels'] = result2['break_levels']
                    return ret
                if result2['continue_levels']:
                    ret['continue_levels'] = result2['continue_levels']
                    return ret
                ret['Success'] = result2['Success']
            if 'Success' in action:
                # action-level Found
                result3 = locate(action['Success'], **opt)
                if result3['break_levels']:
                    ret['break_levels'] = result3['break_levels']
                    return ret
                if result3['continue_levels']:
                    ret['continue_levels'] = result3['continue_levels']
                    return ret
                ret['Success'] = result3['Success']
        else:
            # we didn't find the element
            if 'Failure' in action:
                # action-level NotFound
                result3 = locate(action['Failure'], **opt)
                if result3['break_levels']:
                    ret['break_levels'] = result3['break_levels']
                    return ret
                if result3['continue_levels']:
                    ret['continue_levels'] = result3['continue_levels']
                    return ret
                ret['Success'] = result3['Success']
            else:
                raise RuntimeError(f"element not found, step={pformat(step)}")
    elif locator_type == 'chains':
        # paths must be a list
        paths = action.get('paths', None)
        if type(paths) != list:
            raise RuntimeError(f"chains step 'paths' must be a list, but got {type(paths)}, step={pformat(step)}")

        if dryrun:
            # dryrun is to check syntax only. therefore we don't check the return value.
            for path in paths:
                locator = path.get('locator', None)
                if type(locator) != list:
                    raise RuntimeError(f"chains step 'locator' must be a list, but got {type(locator)}, step={pformat(step)}")
                # now that locator is a list.
                for locator2 in locator:
                    locate(locator2, **opt)
                if 'Success' in path:
                    locate(path['Success'], **opt)
                if 'Failure' in path:
                    locate(path['Failure'], **opt)
            if 'Success' in action:
                locate(action['Success'], **opt)
            if 'Failure' in action:
                locate(action['Failure'], **opt)
            return ret
        
        # collect all the locators in all paths in a list and then call tp_find_element_by_chains()
        chains = []
        for path in paths:
            locator = path.get('locator', None)
            if type(locator) != list:
                raise RuntimeError(f"chains step 'locator' must be a list, but got {type(locator)}, step={pformat(step)}")
            
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
                print(f"matched_paths = {pformat(finder.matched_so_far)}")

            # restore implicit wait
            driver.implicitly_wait(wait_seconds)

            if element:
                ret['Success'] = True
                last_element = element

                # Found. then find which path found the element
                tpdata = getattr(element, 'tpdata', None)
                path_index = tpdata['position']
                print(f"locate_dict: found path_index={path_index} (starting from 0)")

                # update global domstack
                domstack = tpdata['domstack']

                path = paths[path_index]

                if 'Success' in path:
                    # path-level Found
                    result2 = locate(path['Success'], **opt)
                if 'Success' in action:
                    # action-level Found
                    result2 = locate(action['Success'], **opt)

                # always check 'break_levels' first before checking 'Success', because when 'break_levels' is set,
                # we don't care about 'Success'.
                if result2['break_levels']:
                    ret['break_levels'] = result2['break_levels']
                    return ret
                if result2['continue_levels']:
                    ret['continue_levels'] = result2['continue_levels']
                    return ret

                ret['Success'] = result2['Success']           
            else:
                # restore domstack
                replay_domstack(domstack)

                # restore to last element
                element = last_element

                # element = driver.switch_to.active_element
                # last_element = element

                if 'Failure' in action:
                    # action-level NotFound
                    result2 = locate(action['Failure'], **opt)
                    if result2['break_levels']:
                        ret['break_levels'] = result2['break_levels']
                        return ret
                    if result2['continue_levels']:
                        ret['continue_levels'] = result2['continue_levels']
                        return ret
                    ret['Success'] = result2['Success']
                    
                else:
                    raise RuntimeError(f"element not found, step={pformat(step)}")
    else:
        raise RuntimeError(f"unsupported locator_type={locator_type}, step={pformat(step)}")
    
    return ret

def handle_page_change(**opt):
    global locator_driver
    global driver_url
    global driver
    # global last_element
    dryrun = opt.get("dryrun", 0)
    debug = opt.get("debug", 0)

    if dryrun:
        return
    
    # for level in [1,2,3,4]:
    #     print(tpsup.logtools.get_stack(level=level))
    
    if not driver:
        if debug:
            print(f"handle_page_change: driver is None, not initialized yet")
        return

    message = None
    
    if not driver_url:
        message = "driver_url was None"
    elif driver_url != driver.current_url:
        message = f"driver_url changed from {driver_url} to {driver.current_url}"
        
    if message:
        print(f"handle_page_change: update driver_url and locator_driver to driver because {message}")
        locator_driver = driver
        driver_url = driver.current_url
        # print(f"locate: updated last_element to driver.switch_to.active_element")
        # last_element = driver.switch_to.active_element

    if not locator_driver:
        print(f"handle_page_change: locator_driver is None, set it to driver")
        locator_driver = driver


def tp_switch_to_frame(element: WebElement, **opt):
    '''
    the selenium.webdriver.switch_to.frame() is doesn't work perfectly
        for example, it doesn't update
                driver.current_url
                driver.title
        to test
            ptslnm url="file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html" sleep=1 print=url,title "xpath=/html[1]/body[1]/iframe[1]" "iframe" print=url,title "xpath=id('shadow_host')"
            ptslnm url="file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html" sleep=1 print=url,title "xpath=/html[1]/body[1]/iframe[1]" "tp_iframe" print=url,title "xpath=id('shadow_host')" 
        the ending url and title are different.
        'iframe' gave (wrong)
            file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html
            driver.title=Iframe over shadow
        'tp_iframe' gave (correct)
            file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html
            driver.title=child page
        the reason is that 'iframe' only works on http url, not on file:/// url (null origin exception).
        'tp_iframe' gives correct url and title because tp_iframe will force load the url after it caught the exception.
        however, if we disable the exception using "-af" (allow file access), then 'tp_iframe' stops working.
        also, even 'iframe' doesn't give correct url and title, it still can find the element in the iframe.
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
    verbose = opt.get("verbose", debug)
    isExpression = opt.get("isExpression", 0) # for condtion test, we set isExpression=1, so that we get True/False.

    global locator_driver
    global driver
    global driver_url
    global wait_seconds
    global last_element
    global jsr
    global debuggers
    global domstack

    # we don't have a global var for active element, because
    #    - we can always get it from driver.switch_to.active_element
    #    - after we some action, eg, when 'click' is done, the active element is changed; 
    #      it needs to wait to update active element. Therefore, it is better to get it 
    #      from driver.switch_to.active_element in the next step (of locate()).

    ret = {'Success': False, 'break_levels': 0, 'continue_levels': 0}

    # helper = {}  # interactivity helper
    # if interactive:
    #     helper = {
    #         'd': ['dump page', 
    #               dump,
    #               {'driver': driver,
    #                   'output_dir': tpsup.tmptools.tptmp().get_nowdir(mkdir_now=0)}
    #               # we delay mkdir, till we really need it
    #               ],
    #     }

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

    # if not dryrun:
    #     update_locator_driver(**opt)   
    
    locator = correct_xpath(locator)

    '''
    examples can be found in github test folder
    https://github.com/SeleniumHQ/selenium/tree/trunk/py/test
    '''
    # copied from old locate()
    if m := re.match(r"(start_driver|driver)$", locator):
        print(f"locate: start driver")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            driver = get_driver(**opt)
            handle_page_change(**opt)
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
    elif m := re.match(r"(url|url_accept_alert)=(.+)", locator): # shortcuts: newtab, blank
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
            if not driver:
                # start driver (and browser) only when we really need it
                driver = get_driver(**opt)
            tp_get_url(url, accept_alert=accept_alert,
                    interactive=interactive)
            # locator_driver = driver
            handle_page_change(**opt)
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
            # driver_url = driver.current_url
            last_element = driver.switch_to.active_element
            ret['Success'] = True
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
                        
                        if "shadowHosts" in jsr and jsr['shadowHosts']:
                                shadowHosts = jsr['shadowHosts']
                                print(f"locate: jsr shadowHost count={len(shadowHosts)}")

                                for shadowHost in shadowHosts:
                                    locator_driver = shadowHost.shadow_root
                                    url = get_shadowHost_info(shadowHost)
                                    print(f"locate: switch to shadowHost={url}")
                                    domstack.append({
                                        'type': 'shadow',
                                        'element': shadowHost,
                                        'url': url,
                                    })
                                last_element = None # we don't know what the active element is in the shadow root.

                        if "iframeElement" in jsr:
                            iframeElement = jsr['iframeElement']
                            url = iframeElement.get_attribute('src')
                            print(f"locate: switch to iframe={url}") 
                            domstack.append({
                                'type': 'iframe',
                                'element': iframeElement,
                                'url': url,
                            })
                            driver.switch_to.frame(iframeElement)
                            last_element = driver.switch_to.active_element
                        elif "element" in jsr:
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
            handle_page_change(**opt)
    elif m := re.match(r"(dict)(file)?=(.+)", locator, re.MULTILINE | re.DOTALL):
        '''
        'dict' is python code of dict locator. see locate_dict() for details.
        examples:
            dict="{
                'type': 'parallel',
                'action': {
                    'paths' : [
                        {
                            'locator' : 'xpath=//iframe[1]',
                            'Success': 'iframe',
                        },
                        {
                            'locator' : 'css=p',
                            'Success': 'print=html',
                        },
                    ],
                }
            }",

            dictfile=ptslnm_test_dict_parallel.py
        '''
        lang, file, code, *_ = m.groups()

        if file:
            print(f"locate: read {lang} from file {code}")
            with open(code) as f:
                code = f.read()

        print(f"locate: run {lang} code \n{code}")

        if interactive:
            hit_enter_to_continue(helper=helper)
        dict_locator = eval(code)[0]
        print(f"locate: dict_locator=\n{pformat(dict_locator)}")
        ret = locate_dict(dict_locator, **opt)
        handle_page_change(**opt)
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
        # may not be the active element. only clicked element is active.
        # therefore, we use last_element.
        # element = driver.switch_to.active_element
        element = last_element
        
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            # try:
            #     if element.shadow_root:
            #         pass
            # except NoSuchShadowRootException:
            #     print(f'locate: no shadow root under this element')
            #     return
            locator_driver = element.shadow_root  # shadow_driver is a webdriver type
            # last_element = element # last element is unchanged. this is different from iframe.

            url = get_shadowHost_info(element)

            domstack.append({
                'type': 'shadow',
                'element': element,
                'url': url,
            })
            ret['Success'] = True
            # last_element = None # we don't know what the active element is in the shadow root.
            last_element = locator_driver.find_element(By.CSS_SELECTOR, ':first-child')
    elif m := re.match(r"(iframe|tp_iframe|parentIframe|top|tp_top)$", locator):
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

            the selenium.webdriver.switch_to.frame() will not work for cross-origin iframe.
            neither will it work for file url, eg, file:///C:/Users/... by default.
            It doesn't throw exception, but it doesn't update
                     driver.current_url
                     driver.title
            to make it work for file url, we need to set "-af" (allow file access) in ptslnm command line.
            to test
                ptslnm     url="file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html" sleep=1 debug=iframestack "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')"
                ptslnm -af url="file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html" sleep=1 debug=iframestack "xpath=/html[1]/body[1]/iframe[1]" "iframe" "xpath=id('shadow_host')" 
            
                the first errors out: Failed to read a named property 'frameElement' from 'Window': 
                                      Blocked a frame with origin "null" from accessing a cross-origin frame."
                the second works.

            'tp_iframe' was meant to handle cross-origin page, including file url without using "-af".
                tp_iframe will force load the child iframe url after it caught the cross-origin exception.
                but this ruins the page-hierarchy (domstack) because it uses the child iframe url as root url.
                this may not be a concern if our locator chain is one way from parent to child. (most time it is).
                therefore, tp_iframe is not recommended; we may use it only as a last resort.
            to test
                ptslnm     url="file:///C:/Users/tian/sitebase/github/tpsup/python3/scripts/iframe_over_shadow_test_main.html" sleep=1 debug=iframestack "xpath=/html[1]/body[1]/iframe[1]" "tp_iframe" print=url,title "xpath=id('shadow_host')"         

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
   
            if iframe == "iframe":
                # url = driver.current_url # this driver's url, the top level url of the current page.
                # url = driver.execute_script("return document.referrer") # this is the parent url of the iframe
                # url = driver.execute_script("return window.location.href") # this is my (current) iframe url
                url = element.get_attribute('src') # this is child (future) iframe's url
                if not url:
                    url = 'about:srcdoc'

                domstack.append({
                    'type': 'iframe',
                    'element': element,
                    # we need to save url before we switch into iframe.
                    # otherwise, if we need url later, we would have to switch back to this iframe.
                    'url': url,
                })
                driver.switch_to.frame(element)
            elif iframe == "parentIframe":
                while domstack:
                    dom = domstack.pop()
                    if dom['type'] == 'iframe':
                        # driver.switch_to.parent_frame()
                        break
                driver.switch_to.parent_frame()  
            elif iframe == "top":
                domstack.clear()
                driver.switch_to.default_content()
            elif iframe == "tp_top":
                domstack.clear()
                tp_switch_to_top()
            else:
                url = element.get_attribute('src')
                if not url:
                    url = 'about:srcdoc'
                # tp_frame
                domstack.append({
                    'type': 'iframe',
                    'element': element,
                    'url': url,
                })
                tp_switch_to_frame(element, **opt)

            # once we switch into an iframe, we should u+se original driver to locate    
            locator_driver = driver
            driver_url = driver.current_url

            # switch info iframe change the last element to active element.
            # this is different from when we switch into shadow root.
            last_element = driver.switch_to.active_element

            ret['Success'] = True
    elif m1 := get_locator_compiled_path1().match(locator):
        '''
        xpath=/body/div[1]/div[2]/div[3]
        css=body > div:nth-child(1) > div:nth-child(2) > div:nth-child(3)
        click_xpath=/body/div[1]/div[2]/div[3]
        '''
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
            paths_string = paths_string[end_pos:] # leftover string to be processed

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

            handle_page_change(**opt)
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
    elif m := re.match(r"(raw|string|text)=(.+)", locator, re.MULTILINE | re.DOTALL | re.IGNORECASE):
        string_type, value, *_ = m.groups()
        if string_type.lower() != 'raw':
            # replace tab with 4 spaces, because tab will move cursor to the next element.nUX
            value = value.replace("\t", "    ")
        result = locate(f"code2element='''{value}'''", **opt)
        ret['Success'] = result['Success']
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
    #         ret['Success'] = True
    elif m := re.match(r"clear_text", locator):
        # clear text field
        print(f"locate: clear element")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            # if not working, then try to click the element first
            element = driver.switch_to.active_element
            last_element = element

            # https://stackoverflow.com/questions/7732125

            # this clears the element's text but after that, the text field is not active element anymore.
            # element.clear() 

            # the following keeps the element as active element. this is not tested on mac yet.
            element.send_keys(Keys.CONTROL + "a")
            element.send_keys(Keys.DELETE)
            ret['Success'] = True
    elif m := re.match(r"is_empty=(.+)", locator):
        attr, *_ = m.groups()
        print(
            f"locate: check whether '{attr}' is empty.")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            # the checked element may not be the active element.
            # element = driver.switch_to.active_element
            if not last_element:
                raise RuntimeError("no element to check")
            if attr == 'text':
                value = last_element.text
            else:
                value = last_element.get_attribute(attr)
            print(f'{attr} = "{value}"')
            if not (value is None or value == ""):
                raise RuntimeError(f"{attr} is not empty. value={value}")
            ret['Success'] = True
    elif m := re.match(r"sendkey=(.+?)(,\d+)?$", locator, re.IGNORECASE):
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
            
            # a key press may change the page
            handle_page_change(**opt)
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

            # a click may change the page
            handle_page_change(**opt)

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
    elif m := re.match(r"(?:\n|\r\n|\s?)*gone_(xpath|css)=(.+)",
                        locator, re.MULTILINE | re.DOTALL):
        ptype, paths_string = m.groups()

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
    elif m := re.match(r"dump(?:_(element|shadow|iframe|page|all))?(?:-(over))?(=.+)?$", locator):
        scope, dash_args, output_dir, *_ = m.groups()
        if not output_dir:
            # output_dir default to $HOME/dumpdir
            home_dir = driverEnv.get_home_dir()
            output_dir = os.path.join(home_dir, 'dumpdir')
        else:
            output_dir = output_dir[1:] # remove the leading '='
        if not scope:
            scope = 'element'
        print(f"locate: dump {scope} to {output_dir} with args={dash_args}")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            if dash_args and 'over' not in dash_args:
                # default dump is to clean up the output_dir before we dump.
                # 'over' means we don't clean up the output_dir
                print(f"locate: clean up {output_dir}")
                shutil.rmtree(output_dir, ignore_errors=True)
            dump(output_dir, scope=scope, **opt)
            ret['Success'] = True
    # end of old send_input()

    # the following are new features
    elif m := re.match(r"(impl|expl|script|page)*wait=(\d+)", locator):
        # implicit wait
        wait_type, value, *_ = m.groups()
        if not wait_type:
            wait_type = 'all'
        print(f"locate: set {wait_type} wait type to {value} seconds")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            if not driver:
                driver = get_driver(**opt)
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
    elif locator == 'refresh':
        print(f"locate: refresh driver")
        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            driver.refresh()
            locator_driver = driver
            last_element = None
            ret['Success'] = True
            handle_page_change(**opt)
    elif m := re.match(r"comment=(.+)", locator, re.MULTILINE | re.DOTALL):
        ret['Success'] = True # hard code to True for now
        commnet, *_ = m.groups()
        print(f"locate: comment = {commnet}")
        # for fancier comment, we can use 
        #   code='print(f"a+b={a+b}")'
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
    elif m := re.match(r"(print|debug(?:_before|_after)*)=((?:(?:\b|,)(?:consolelog|css|domstack|element|html|iframestack|tag|text|title|timeouts|url|waits|xpath))+)$", locator):
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
        if not dryrun:
            if directive == 'print':
                print(f"locate: get property {keys}")
                for key in keys:
                    if not dryrun:
                        if key == 'consolelog':
                            print_js_console_log()
                        elif key == 'css':
                            if last_element:
                                css = js_get(last_element, 'css', **opt)
                                print(f'element_css={css}')
                        elif key == 'domstack':
                            print_domstack()
                        elif key == 'element':
                            if last_element:
                                js_print_debug(last_element)
                            else:
                                print(f'element is not available because last_element is None')
                        elif key == 'html':
                            if last_element:
                                html = last_element.get_attribute('outerHTML')
                                print(f'element_html=element.outerHTML={html}')   
                            else:
                                print(f'element_html is not available because last_element is None')
                        elif key == 'iframestack':
                            print_iframestack()
                        elif key == 'tag':
                            # get element type
                            if last_element:
                                tag = last_element.tag_name
                                print(f'element_tag_name=element.tag_name={tag}')
                        elif key == 'text':
                            if last_element:
                                text = last_element.text
                                print(f'element.text={text}')
                        elif key == 'title':
                            title = driver.title
                            print(f'driver.title={title}')
                        elif key == 'timeouts' or key == 'waits':
                            # https://www.selenium.dev/selenium/docs/api/py/webdriver_chrome/selenium.webdriver.chrome.webdriver.html
                            # https://www.selenium.dev/selenium/docs/api/java/org/openqa/selenium/WebDriver.Timeouts.html
                            print(f'    explicit_wait={wait_seconds}')    # we will run WebDriverWait(driver, wait_seconds)
                            print(f'    implicit_wait={driver.timeouts.implicit_wait}') # when we call find_element()
                            print(f'    page_load_timeout={driver.timeouts.page_load}') # driver.get()
                            print(f'    script_timeout={driver.timeouts.script}') # driver.execute_script()
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
                        elif key == 'xpath':
                            if last_element:
                                xpath = js_get(last_element, 'xpath', **opt)
                                print(f'element_xpath={xpath}')
                            else:
                                print(f'element_xpath is not available because last_element is None')
            else:
                # now for debugs
                if directive == 'debug_before':
                    before_after = 'before'
                else:
                    # directive == 'debug_after' or directive == 'debug'
                    before_after = 'after'

                action = f"print={keys_string}"
                debuggers[before_after] = [action]
                print(f"locate: debuggers[{before_after}]={pformat(debuggers[before_after])}")
    elif result := handle_break(locator, **opt):
        if not dryrun:
            # not dryrun, we check the result
            # we found the expected break
            ret['break_levels'] = result['break_levels']
            ret['continue_levels'] = result['continue_levels']
            # when matched any break statement, we break, no matter 'Success' is True or False.
    else:
        raise RuntimeError(f"unsupported 'locator={locator}'")
    
    return ret

# add 'locate' function to helper only after defined 'locate'

helper['l'] = {
    'desc': 'run a locate command',
    'func': locate, # type: ignore
    'args': {
        'fromUser': True
    },
    'usage': f'''
    run a locate command. Examples
    l tab=1
    l click
    all locators:
    {"\n".join(get_defined_locators(locate))}
    ''',
}

def get_shadowHost_info(shadowHost: WebElement):
    # we pick id, name, or tag_name as the shadow root's name
    url = shadowHost.get_attribute('id')
    if not url:
        url = shadowHost.get_attribute('name')
    if not url:
        url = shadowHost.tag_name
    return url


def download_chromedriver(**opt):
    '''
    download webdriver for selenium
    '''
    # https://pypi.org/project/webdriver-manager/
    # we only on-demand load webdriver_manager, so that we don't need to install it if we don't use it.
    from webdriver_manager.chrome import ChromeDriverManager

    driver_version = opt.get('driver_version', None)
    driver_path = ChromeDriverManager(driver_version=driver_version).install()
    # driver_path = /Users/tian/.wdm/drivers/chromedriver/mac64/116.0.5845.179/chromedriver-mac-arm64/chromedriver
    print(f'downloaded driver_path = {driver_path}')

    # run chromedriver --version to see the version
    cmd = f"{driver_path} --version"
    print(cmd)
    os.system(cmd)

procs = [
            "chromedriver", # chromedriver
        ]

# the following is for batch framework - batch.py
#
# pre_batch and post_batch are used to by batch.py to do some setup and cleanup work
# '
# known' is only available in post_batch, not in pre_batch.

def pre_batch(all_cfg, known, **opt):
    # init global variables.
    # SeleniumEnv class doesn't need global vars because it is Object-Oriented
    # but batch.py uses global vars to shorten code which will be eval()/exec()
    global driverEnv

    log_FileFuncLine(f"running pre_batch()")
    if all_cfg["resources"]["selenium"].get('driverEnv', None) is None:
        # driverEnv is created in delayed mode
        method = all_cfg["resources"]["selenium"]["driver_call"]['method']
        kwargs = all_cfg["resources"]["selenium"]["driver_call"]["kwargs"]
        # driverEnv = method(**kwargs)
        driverEnv = method(**{**kwargs, **opt})
        # 'host_port' are in **opt
        all_cfg["resources"]["selenium"]['driverEnv'] = driverEnv
        log_FileFuncLine(f"driverEnv is created in batch.py's delayed mode")

def post_batch(all_cfg, known, **opt):
    dryrun = opt.get('dryrun', False)
    print("")
    print("--------------------------------")

    if dryrun:
        print("dryrun, skip post_batch()")
        return
    
    print(f"running post_batch()")

    if driver:
        print(f"driver is still alive, quit it")
        driver.quit()

    log_FileFuncLine(f"kill chromedriver if it is still running")
    tpsup.pstools.kill_procs(procs, **opt)

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
        'clean': {
            "switches": ["-clean", "--clean"],
            "default": False,
            "action": "store_true",
            "help": "clean chrome persistence dir and driver log",
        },
        'cleanQuit': {
            "switches": ["-cq", "--cleanQuit"],
            "default": False,
            "action": "store_true",
            "help": "clean chrome persistence dir and driver log then quit",
        },
        'js': {
            'switches': ['-js', '--js'],
            'default': False,
            'action': 'store_true',
            'help': 'run locator in js. js only accept locators: xpath, css, shadow, or iframe'
        },
        'trap': {
            'switches': ['-trap', '--trap'],
            'default': False,
            'action': 'store_true',
            'help': 'used with -js, to add try{...}catch{...}',
        },
        'full': {
            'switches': ['-full', '--full'],
            'default': False,
            'action': 'store_true',
            'help': 'print full xpath in levels, not shortcut, eg. /html/body/... vs id("myinput")',
        },
        'limit_depth': {
            'switches': ['--limit_depth'],
            'default': 5,
            'action': 'store',
            'type': int,
            'help': 'limit scan depth',
        },
        'allowFile': {
            'switches': ['-af', '--allowFile'],
            'default': False,
            'action': 'store_true',
            'help': "allow file:// url; otherwise, we get 'origin' error in console log when switch iframe. but this is security risk. use for testing only",
        },
    },
    "resources": {
        "selenium": {
            # "method": tpsup.seleniumtools.get_driver,
            # "method": get_driver,
            "method": SeleniumEnv,
            # "cfg": {},

            "init_resource": 0,  # delay init until first use. this logic is in batch.py
        },
    },
}


def main():
    test_basic()
    pass


if __name__ == "__main__":
    main()
