import os
import re
import sys
import time
import subprocess
from urllib.parse import urlparse
from shutil import which
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


class SeleniumEnv:
    def __init__(self, host_port: str = 'auto', page_load_timeout: int = 15, **opt):
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

        self.page_load_timeout = page_load_timeout

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
            sys.stderr.write(f"pwd={os.getcwd()}\n")
            sys.stderr.write(f'PATH={os.environ["PATH"]}\n')

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
                    sys.stderr.write(f"cmd={cmd}\n")
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

            sys.stderr.write(f"check browser port at {host_port}\n")
            self.connected_existing_browser = False
            (host, port) = host_port.split(":", 1)
            if is_tcp_open(host, port):
                sys.stderr.write(
                    f"{host_port} is open. let chromedriver to connect to it\n")
            else:
                raise RuntimeError(f"browser host_port={host_port} is not open.\n")

        if host_port == "auto":
            sys.stderr.write(
                "chromedriver will auto start a browser and pick a port\n")

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
                self.browser_options.add_argument("--headless")
                sys.stderr.write(" in headless mode\n")
        else:
            host, port = host_port.split(":", 1)
            self.browser_options.add_argument(
                f"--remote-debugging-port={port}")
            # self.browser_options.add_argument(f'--remote-debugging-address=127.0.0.1')

            if host.lower() != "localhost" and host != "127.0.0.1" and host != "":
                if self.dryrun:
                    sys.stderr.write(
                        "cannot connect to remote browser, but this is dryrun, so we continue\n"
                    )
                else:
                    raise RuntimeError("cannot connect to remote browser.")
            else:
                sys.stderr.write(
                    "cannot connect to an existing local browser. we will start up one.\n")
                self.browser_options.binary_location = get_browser_path()

                if self.headless:
                    self.browser_options.add_argument("--headless")
                    sys.stderr.write(" in headless mode\n")
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

        for arg in opt.get("browserArgs", []):
            self.browser_options.add_argument(f"--{arg}")
            # chrome_options.add_argument('--proxy-pac-url=http://pac.abc.net')  # to run with proxy

        print(
            f"browser_options.arguments = {pformat(self.browser_options.arguments)}")

        if self.dryrun:
            sys.stderr.write(
                "this is dryrun, therefore, we don't start a webdriver, nor a browser\n"
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
            sys.stderr.write("started\n")
            # if self.headless:
            #    time.sleep(1)  # throttle for the headless mode

            # set timeout
            # https://stackoverflow.com/questions/17533024/how-to-set-selenium-python-webdriver-default-timeout
            self.driver.set_page_load_timeout(
                self.page_load_timeout
            )  # for chromedriver.
            # other driver use implicitly_wait()
            # The default value for implicitly_waits is 0, which means
            # (and always has meant) "fail findElement immediately if
            # the element can't be found."
            # You shouldn't be receiving a TimeoutException directly
            #  from findElement.
            # You'll likely only be receiving that when using a
            #  so-called "explicit wait", using the WebDriverWait construct.
            # the code is at
            # lib\webdriver line 1353:
            # webdriver.Command(webdriver.CommandName.IMPLICITLY_WAIT).
            #      setParameter('ms', ms < 0 ? 0 : ms)

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


def print_js_console_log(driver: webdriver.Chrome, **opt):
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
    env = tpsup.envtools.Env()
    env.adapt()
    static_setup = {}
    if env.isWindows:
        # as of now, only windows has static setup
        static_browser_path = f"{os.environ['SITEBASE']}/{env.system}/{env.os_major}.{env.os_minor}/Chrome/Application/chrome.exe"
        static_browser_path = os.path.normpath(static_browser_path)
        # maily for cygwin/gitbash, to convert /cydrive/c/users/... to c:/users/...
        static_setup['chrome'] = static_browser_path
        # print(f"static_setup['chrome']={static_setup['chrome']}")

        static_driver_path = f"{os.environ['SITEBASE']}/{env.system}/{env.os_major}.{env.os_minor}/chromedriver/chromedriver.exe"
        static_driver_path = os.path.normpath(static_driver_path)
        # maily for cygwin/gitbash, to convert /cydrive/c/users/... to c:/users/...
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
            print(f"static setup configured {exec}={static_path}")
            if os.path.isfile(static_path):
                path = static_setup[exec]
                print(f"static setup's {exec}={static_path} exists.")
            else:
                print(f"static setup's {exec}={static_path} doesn't exist.")

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
            print(f"found {exec}={path} in PATH")
            found_path[exec] = path
        else:
            print(f"cannot find {exec} in PATH={os.environ['PATH']}")

    if opt.get('compareVersion', 0):
        print("")
        chrome_vesion = None
        chromedriver_vesion = None

        if found_path.get('chrome'):
            chrome_version_full_path = which('chrome_version')

            if not chrome_version_full_path:
                raise RuntimeError(
                    f"cannot find 'chrome_version' command in PATH={os.environ['PATH']}")

            chrome_vesion = str(subprocess.check_output(
                [chrome_version_full_path, found_path['chrome']]).strip(), 'utf-8')
            # 99.0.4844.74

            # use str() to convert bytes to string

            print(f"chrome version={chrome_vesion}")

            chrome_major = chrome_vesion.split('.')[0]

            print(f"chrome major={chrome_major}")

        if found_path.get('chromedriver'):
            chromedriver_vesion = str(subprocess.check_output(
                [found_path['chromedriver'], '--version']).strip(), 'utf-8')
            # ChromeDriver 99.0.4844.51 (d537ec02474b5afe23684e7963d538896c63ac77-refs/branch-heads/4844@{#875})

            # use str() to convert bytes to string

            print(f"chromedriver version={chromedriver_vesion}")

            chromedriver_vesion = chromedriver_vesion.split()[1]
            # 99.0.4844.74

            print(f"chromedriver version={chromedriver_vesion}")

            chromedriver_major = chromedriver_vesion.split('.')[0]
            chromedriver_major = chromedriver_major

            print(f"chromedriver version={chromedriver_vesion}")

        if chrome_vesion and chromedriver_vesion:
            if chrome_major != chromedriver_major:
                print(
                    f"chrome major version {chrome_major} doesn't match chromedriver major version {chromedriver_major}")
                raise RuntimeError(
                    f"chrome major version {chrome_major} doesn't match chromedriver major version {chromedriver_major}")
            else:
                print(
                    f"chrome major version {chrome_major} matches chromedriver major version {chromedriver_major}")
    return found_path


# https://stackoverflow.com/questions/47420957/create-custom-wait-until-condition-in-python


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
                tp_click(driver, e)

            print(f'found {ptype}="{path}"')

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


we_return = 0  # global var, note: only global to this filewe_return
action_data = {}  # global var


def run_actions(driver: webdriver.Chrome, actions: List, **opt):
    dryrun = opt.get("dryrun", 0)
    interactive = opt.get("interactive", 0)
    print_console_log = opt.get("print_console_log", 0)
    debug = opt.get("debug", 0)

    # we don't need these in python as we pass driver and element in function. when we exec(),
    #     global we_return, driver, element
    #     driver = _driver

    global we_return  # global var, note: only global to this file
    global action_data

    we_return = 0
    if not opt.get('keep_action_data', 0):
        action_data = {}

    element: WebElement = None

    # for row in actions:
    for i in range(0, len(actions)):
        row = actions[i]
        sys.stdout.flush()

        #   locator                             input         comment
        # [ 'xpath=//botton[@id="Submit"',     'click',       'Submit' ]
        locator, input, comment, *rest = row + [None] * 3

        if comment is not None:
            print(f"{comment}")

        if locator is not None:
            element = locate(driver, locator, **opt)
            # we will pass back element for caller's convenience. In theory, the caller could also
            # use the following to get it.
            #      element = driver.switch_to.active_element
            # but if we didn't do
            #      element.click()
            # then it may not be active element. In this case, caller can use below to get the element.
            globals()['element'] = element
            # we don't need to do the same for driver. As Python function uses pass-by-reference,therefore
            # driver stays the same.
            # globals()['driver'] = driver

            if print_console_log:
                print_js_console_log(driver)

        if debug:
            js_print_debug(driver, element)

        if we_return:
            # we return globals() here because exec()'s effect are only in globals().
            # globals() are only from to this module file, not the caller's globals().
            return globals()

        send_input(driver, element, input, **opt)

        if print_console_log:
            print_js_console_log(driver)

        if we_return:
            return globals()

    return globals()


def tp_get_url(driver: webdriver.Chrome, url: str, **opt):
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
        print(f"\nseen 'TimeoutException receiving message from renderer' again? do driver.refresh(). If this doesn't help, then set page_load_timeout longer.\n")
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
            WebDriverWait(driver, 3).until(EC.alert_is_present(),
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


locator_driver: webdriver = None
driver_url = None


def locate(driver: webdriver.Chrome, locator2: Union[str, dict], **opt):
    dryrun = opt.get("dryrun", 0)
    interactive = opt.get("interactive", 0)
    debug = opt.get("debug", 0)

    helper = {}  # interactivity helper
    if interactive:
        helper = {
            'd': ['dump page', dump,
                  {'driver': driver,
                      'output_dir': tpsup.tmptools.tptmp().get_nowdir(mkdir_now=0)}
                  # we delay mkdir, till we really need it
                  ],
        }

    global we_return
    global action_data

    element = None
    #
    # example of actions:
    #
    #     actions = [
    #         [ 'xpath=/a/b,xpath=/a/c', 'click', 'string locator' ],
    #         [ ['xpath=/a/b', 'shadow', 'css=d'], 'click', 'chain locator'],
    #         [
    #             {
    #                 'locator' : 'xpath=/a/b,xpath=/a/c',
    #                 'NotFound' : 'print("not found")',
    #             },
    #             'click',
    #             'use hash for the most flexibility'
    #         ],
    #         [
    #             '''
    #                 xpath=//dhi-wc-apply-button[@applystatus="true"],
    #                 xpath=//dhi-wc-apply-button[@applystatus="false"],
    #             ''',
    #             {
    #                 0: 'code=' + '''
    #                                     action_data['error'] = "applied previously"
    #                                     we_return=1
    #                                     ''',
    #                 1: None,
    #             },
    #             'find applied or not. If applied, return'
    #         ],
    #         [
    #             {
    #                 'chains': [
    #                     # branch in the beginning
    #                     [
    #                         'xpath=/html/body[1]/ntp-app[1]', 'shadow',
    #                         'css=#mostVisited', 'shadow',
    #                         'css=#removeButton2',  # correct on ewould be 'css=#removeButton'. we purposefully typoed
    #                     ],
    #                     [
    #                         'xpath=/html/body[1]/ntp-app[1]', 'shadow',
    #                         'css=#mostVisited', 'shadow',
    #                         'css=#actionMenuButton'
    #                     ],
    #                 ],
    #             },
    #             {
    #                 # first number is the chain number, followed by locator number
    #                 '0.0.0.0.0.0': 'code=print("found remove button")',
    #                 '1.0.0.0.0.0': 'code=print("found action button")',
    #             },
    #             "test chains",
    #         ],
    #     ],

    if (type(locator2) == dict) and ('chains' in locator2):
        h = locator2
        print(f"locate(): search for chains = {pformat(h['chains'])}")

        if interactive:
            hit_enter_to_continue(helper=helper)
        if not dryrun:
            # https://selenium-python.readthedocs.io/waits.html
            wait = WebDriverWait(driver, 10)
            finder = tp_find_element_by_chains(h['chains'], **opt)

            try:
                # wait.until() takes the object.
                # note: here we used finder, not finder(driver).
                element = wait.until(finder)
            except Exception as ex:
                print(f"locate failed. {ex}")
                print(f"matched_paths = {pformat(finder.matched_paths)}")

            if element is None:
                code = h.get("NotFound", None)
                if code is not None:
                    print(f"NotFound code: {code}")
                    if code == 'pass':
                        # try to reduce exec() times
                        pass
                    else:
                        exec_into_globals(code, globals(), locals())
                else:
                    raise RuntimeError(f"none of paths found")
            if element is None:
                element = driver.switch_to.active_element

            if tpdata := getattr(element, 'tpdata', None):
                print(f"tpdata = {pformat(tpdata)}")
        return element

    h = {}  # hash
    if (not locator2) or (type(locator2) == str):
        h["locator"] = [locator2]
    elif type(locator2) == list:
        h["locator"] = locator2
    elif type(locator2) == dict:
        h = locator2
        if type(h["locator"]) == str:
            h["locator"] = [h["locator"]]
    else:
        raise RuntimeError(
            f"unsupported locator data type {pformat(locator2)}")

    print(f"h={pformat(h)}")

    locator_chain = h["locator"]

    # locator_driver vs original 'driver'
    #    - we introduce locator_driver because shadow_host.shadow_root is also a driver,
    #      we can call it shadow driver, but its locator can only see the shadow DOM,
    #      and only css locator is supported as of 2022/09/09.
    #    - locator_driver started as the original driver.
    #    - locator_driver will be shadow driver when we are in a shadow root.
    #    - locator_driver will be (original) driver after we switch_to an iframe, even if
    #      the iframe is under a shadow root.
    #    - every time driver_url changes, we should reset locator_driver to driver.
    #      driver_url can be changed not only by get(url), but also by click()
    # shadow driver only has a few attributes, just to support the separate DOM, the shadow DOM.
    #     - find_element
    #     - find_elements
    # pycharm hint also only shows the above two attributes from a shadow driver.
    # for example, shadow_host.shadow_root cannot
    #      - get(url)
    #      - switch_to
    #      - click()
    # therefore, we don't need to pass 'locator_driver' to send_input().
    global locator_driver
    global driver_url
    if (not locator_driver) or (not driver_url) or (driver_url != driver.current_url):
        locator_driver = driver
        driver_url = driver.current_url

    # https://selenium-python.readthedocs.io/locating-elements.html
    for locator in locator_chain:
        if not locator:  # None, empty, 0
            print(f"locate(): no locator")
        elif m := re.match(r"(url|url_accept_alert)=(.+)", locator):
            tag, url, *_ = m.groups()
            accept_alert = 0
            if tag == 'url_accept_alert':
                accept_alert = 1
            print(f"locate(): go to url={url}, accept_alert={accept_alert}")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                tp_get_url(driver, url, accept_alert=accept_alert,
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
        elif m := re.match(r"code=(.+)", locator, re.MULTILINE | re.DOTALL):
            code, *_ = m.groups()
            print(f"action: run python code = {code}")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                exec_into_globals(code, globals(), locals())
                if we_return:
                    return
        elif m := re.match(r"js=(.+)", locator, re.MULTILINE | re.DOTALL):
            js, *_ = m.groups()
            print(f"locate(): execute js={js}\n")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                element = driver.execute_script(js)
        elif m := re.match(r"tab=(.+)", locator):
            count_str, *_ = m.groups()
            count = int(count_str)
            print(f"locate(): tab {count} times")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                driver.switch_to.active_element.send_keys(Keys.TAB * count)
        elif m := re.match(r"shifttab=(.+)", locator):
            count_str, *_ = m.groups()
            count = int(count_str)
            print(f"locate(): tab backward (shift+tab) {count} times")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                ac = ActionChains(driver)
                ac.key_down(Keys.SHIFT)
                for i in range(0, count):
                    ac.send_keys(Keys.TAB)
                ac.key_up(Keys.SHIFT)
                ac.perform()
        elif locator == "shadow":
            print(f"locate(): switch into shadow_root")
            try:
                if element.shadow_root:
                    pass
            except NoSuchShadowRootException:
                print(f'no shadow root under this element')
                return
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                locator_driver = element.shadow_root  # shadow_driver is a webdriver type
        elif locator == "iframe":
            print(f"locate(): switch into iframe")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                # we cannot use locator_driver to swith iframe when locator_driver is a shadow root.
                #   locator_driver.switch_to.frame(element)
                #   AttributeError: 'ShadowRoot' object has no attribute 'switch_to'
                # Therefore, we use (original) driver

                driver.switch_to.frame(element)
                locator_driver = driver
                # once we switch into an iframe, we should use original driver to locate
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

            print(f"locate(): search for paths = {pformat(type_paths)}")

            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                # here we use 'locator_driver' so that we are in the correct DOM
                wait = WebDriverWait(locator_driver, 10)  # seconds

                element = None
                # this is needed; otherwise, if element is defined, a failed 'try' below
                # will not set element to None.

                finder = tp_find_element_by_paths(type_paths, **opt)

                try:
                    # https://selenium-python.readthedocs.io/waits.html
                    element = wait.until(finder)
                    # element = wait.until(find_element_by_xpath('//input[@name="q"]'))
                except:
                    print(f"locate failed")

                if element is None:
                    code = h.get("NotFound", None)
                    if code is not None:
                        print(f"NotFound code: {code}")
                        if code == 'pass':
                            # try to reduce exec() times
                            pass
                        else:
                            exec_into_globals(code, globals(), locals())
                    else:
                        raise RuntimeError(f"none of paths found")
                    break
        else:
            raise RuntimeError(f"unsupported 'locator={locator}'")

    if element is None:
        # some locators don't explicitly return an element, therefore, we set it here.
        element = driver.switch_to.active_element

    return element


def send_input(
    driver: webdriver.Chrome,
    element: WebElement,
    input: Union[str, List[str], None],
    **opt,
):  # list vs List[int] or List[str]
    dryrun = opt.get("dryrun", 0)
    interactive = opt.get("interactive", 0)
    humanlike = opt.get("humanlike", 0)
    debug = opt.get("debug", 0)

    global we_return
    global action_data
    if we_return:
        # this could be set by locator's NotFound code
        return

    if input is None or input == "":
        print(f"action: no input")
        return

    steps = []

    if debug:
        print(f"input={pformat(input)}")

    input_type = type(input)

    if input_type == str:
        steps.append(input)
    elif input_type == list:
        steps.extend(input)
    elif input_type == dict:
        # input = {
        #     0:  'click',
        #     1: ['click', 'sleep=1'],
        #     2: 'code=pass',
        # }
        tpdata = getattr(element, 'tpdata', None)
        if tpdata:
            position = tpdata['position']
            if position in input:
                input2 = input[position]

                if input2 is None or input2 == "":
                    print(f"action: no input")
                    return

                if type(input2) == str:
                    steps.append(input2)
                elif type(input2) == list:
                    steps.extend(input2)
                else:
                    raise RuntimeError(f"input[{position}] type={type(input2)} is not supported. "
                                       f"input={pformat(input)}")
            else:
                raise RuntimeError(
                    f"position={position} is not defined in input={pformat(input)}")
        else:
            raise RuntimeError(f"tpdata is not available from element")
    else:
        raise RuntimeError(
            f"send_input type={input_type} is not supported. input={pformat(input)}")

    if not interactive and humanlike:
        human_delay()

    helper = {}  # interactivity helper
    if interactive:
        helper = {
            'd': ['dump page', dump,
                  {'driver': driver,
                      'output_dir': tpsup.tmptools.tptmp().get_nowdir(mkdir_now=0)}
                  # we delay mkdir, till we really need it
                  ],
        }

    for step in steps:
        if step == "debug":
            js_print_debug(driver, element)
        elif m := re.match(r"code=(.+)", step, re.MULTILINE | re.DOTALL):
            code, *_ = m.groups()
            print(f"action: run python code = {code}")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                exec_into_globals(code, globals(), locals())
                if we_return:
                    return
        elif m := re.match(r"js=(.+)", step, re.MULTILINE | re.DOTALL):
            js, *_ = m.groups()
            print(f"action: run js code = {js}")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                # if we need an element from the result, call it from locate()
                driver.execute_script(js)
        elif m := re.match(r"sleep=(.+)", step):
            seconds, *_ = m.groups()
            print(f"action: sleep {seconds}")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                time.sleep(int(seconds))
        elif m := re.match(r"hover=(.+)", step):
            seconds_str, *_ = m.groups()
            seconds = int(seconds_str)
            print(f"action: hover {seconds} seconds")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                ActionChains(driver).move_to_element(
                    element).pause(seconds).perform()
        elif m := re.match(r"string=(.+)", step):
            # even if only capture group, still add *_; other string would become list, not scalar
            string, *_ = m.groups()
            print(f'action: type string = "{string}"')
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                element.send_keys(string)
        elif m := re.match(r"clear_attr=(.+)", step):
            # even if only capture group, still add *_; other attr would become list, not scalar
            attr, *_ = m.groups()
            print(f"action: clear {attr}")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                value = element.get_attribute(attr)
                if not value is None:
                    length = len(value)
                    key = "backspace"
                    print(f"typing {key} {length} times")
                    element.send_keys(
                        Keys.__getattribute__((Keys, key.upper())) * length
                    )
        elif m := re.match(r"is_attr_empty=(.+)", step):
            attr, *_ = m.groups()
            print(
                f"action: check whether {attr} is empty. If yes, we will do next step")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                value = element.get_attribute(attr)
                print(f'{attr} = "{value}"')
                if not (value is None or value == ""):
                    return
        elif m := re.match(r"key=(.+?),(.+)", step):
            key, count_str = m.groups()
            count = int(count_str)
            print(f"action: type {key} {count} times")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                element.send_keys(Keys.__getattribute__(
                    Keys, key.upper()) * count)
        elif m := re.match(r"tab=(.+)", step):
            count_str, *_ = m.groups()
            count = int(count_str)
            print(f"action: tab {count} times")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                driver.switch_to.active_element.send_keys(Keys.TAB * count)
        elif step == "click":
            print(f"action: {step}")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                tp_click(driver, element)
        elif m := re.match(r"select=(value|index|text),(.+)", step):
            attr, string = m.groups()
            print(f'action: select {attr} = "{string}"')
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                se = Select(element)
                if attr == "value":
                    se.select_by_value(string)
                elif attr == "index":
                    se.select_by_index(int(string))
                else:
                    # attr == 'text'
                    se.select_by_visible_text(string)
        elif m1 := re.match(r"(?:\n|\r\n|\s?)*gone_(xpath|css)=(.+)",
                            step, re.MULTILINE | re.DOTALL):
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

            interval = opt.get("gone_interval", 60)

            print(
                f"action: wait {interval} seconds for elements gone, paths = {pformat(type_paths)}")

            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                e = None
                i = 0

                while i < interval:
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
                            print(f"all paths gone in {i} seconds")
                            break
                if e:
                    js_print_debug(driver, e)
                    raise RuntimeError(f"not all paths gone in {i} seconds")
        elif (step == "iframe"):
            print(f"action: switch iframe")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                driver.switch_to.frame(element)
        elif (step == "default_iframe"):
            print(f"action: switch back to default iframe")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                driver.switch_to.default_content()

        elif m := re.match(r"dump_(element|all)=(.+)", step):
            scope, output_dir, *_ = m.groups()
            print(f"action: dump {scope} to {output_dir}")

            # output_dir can be from both **opt and step, to avoid the multiple-values error,
            # we group output_dir into **opt, allowing override kwargs
            #
            if scope == 'all':
                dump(driver, **{**opt, 'output_dir': output_dir})
            else:
                if element is None:
                    print(
                        "dump_element() is called but element is None, we dump_all() instead")
                dump(driver, element=element, **
                     {**opt, 'output_dir': output_dir})
        elif m := re.match(r"we_return=(.+)", step):
            we_return, *_ = m.groups()
            print(f"we_return={we_return}")

            if we_return:
                return globals()
        else:
            raise RuntimeError(f'unsupported input step="{step}"')


def dump(driver: webdriver.Chrome, output_dir: str, element: WebElement = None, **opt):
    verbose = opt.get('verbose', 0)

    source_file = f"{output_dir}/source.html"
    os.makedirs(output_dir, exist_ok=True)  # this is mkdir -p
    with open(source_file, "w", encoding="utf-8") as source_fh:
        if element:
            source_fh.write(element.get_attribute('outerHTML'))
        else:
            source_fh.write(driver.page_source)
        source_fh.close()

    if element is None:
        iframe_list = driver.find_elements(By.XPATH, '//iframe')
        # wait = WebDriverWait(driver, 20)
        # iframe_list = wait.until(EC.presence_of_all_elements_located((By.XPATH, '//iframe')))
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
        dump_deeper(driver, iframe, dump_state, 'iframe', **opt)

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
        dump_deeper(driver, element, dump_state, 'shadow',
                    **opt)  # don't forget element itself

    for e in start_node.find_elements(By.XPATH, find_path):
        dump_deeper(driver, e, dump_state, 'shadow', **opt)

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


def dump_deeper(driver: webdriver, element: WebElement, dump_state: dict, type: str, **opt):
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
                xpath = js_get(driver, element, 'xpath', **opt)
                print(f'no shadow root under xpath={xpath}')
            return

    print(f"dump_state = {pformat(dump_state)}")
    print(f"type = {type}")

    # selenium.common.exceptions.StaleElementReferenceException: Message: stale element reference:
    #   element is not attached to the page document
    xpath: str = None
    css: str = None

    try:
        xpath = js_get(driver, element, 'xpath', **opt)
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
            css = js_get(driver, element, 'css', **opt)
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
        driver.switch_to.frame(element)
        with open(output_file, "w", encoding="utf-8") as ofh:
            ofh.write(driver.page_source)
            ofh.close()

        # find sub iframes in this frame
        iframe_list = driver.find_elements(By.XPATH, '//iframe')
        for sub_frame in iframe_list:
            dump_deeper(driver, sub_frame, dump_state, 'iframe', **opt)

        # find shadows in this frame
        for e in driver.find_elements(By.XPATH, "//*"):
            dump_deeper(driver, e, dump_state, 'shadow', **opt)

        driver.switch_to.default_content()  # don't forget to switch back

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
            dump_deeper(driver, iframe, dump_state, 'iframe', **opt)

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
            dump_deeper(driver, e, dump_state, 'shadow', **opt)

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
    js_list: list = []
    trap = opt.get('trap', 0)

    js = 'var e = document'
    for locator in locator_chain:
        if m := get_locator_compiled_path1().match(locator):
            ptype, path = m.groups()
            if ptype == 'xpath':
                js += f'.evaluate("{path}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue'
            elif ptype == 'css':
                js += f'.querySelector("{path}")'
            else:
                raise RuntimeError(
                    f"unsupported ptype={ptype} in locator={locator}")
        elif locator == 'shadow':
            js += '.shadowRoot'
        elif locator == 'iframe':
            # https://stackoverflow.com/questions/7961229/

            # cd(iframe_element) only works in Firefox
            # js += '.contentWindow;\ncd(element);\nelement = document'
            #             js += ''';
            # const current_origin = window.location.origin;
            #
            # var iframe_src = e.getAttribute('src');
            # // alert(`iframe_src=${iframe_src}`);
            # var iframe_url = null
            # var iframe_origin = null
            # if (iframe_src) {
            #     //https://developer.mozilla.org/en-US/docs/Web/API/URL/origin
            #     iframe_url = new URL(iframe_src);
            #     // console.log(`iframe_url=${iframe_url}`);
            #     alert(`iframe_url=${iframe_url}`);
            #     iframe_origin = iframe_url.origin;
            # }
            #
            # var iframe_inner = null;
            # if ( (!iframe_origin) || (current_origin.toUpperCase() === iframe_origin.toUpperCase()) ) {
            #     //case-insensitive compare
            #     console.log(`iframe stays in the same origin ${current_origin}`); // note to use backticks
            #     iframe_inner=e.contentDocument || e.contentWindow.document;
            #     document = iframe_inner
            # } else {
            #     console.log(`iframe needs new url ${iframe_url}`);  // note to use backticks
            #     window.location.replace(iframe_url);
            # }
            #     '''
            js += '''
try {
    let iframe_inner = e.contentDocument || e.contentWindow.document;
    document = iframe_inner
    const current_origin = window.location.origin;
    console.log(`iframe stays in the same origin ${current_origin}`); // note to use backticks
} catch(err) {
    let iframe_src = e.getAttribute('src');
    //iframe_url = new URL(iframe_src);
    iframe_url = iframe_src;
    console.log(`iframe needs new url ${iframe_url}`);  // note to use backticks
    window.location.replace(iframe_url);
}
            '''
            # save one js after very iframe
            if trap:
                js = wrap_js_in_trap(js)
            js_list.append(js)

            # start another js
            js = 'var e = document'
        else:
            raise RuntimeError(f"unsupported locator={locator}")

    # save the last js.
    #   - only the last js 'return e'
    #   - the intermediate js were all ending with iframes
    js += ';\nreturn e'
    if trap:
        js = wrap_js_in_trap(js)
    js_list.append(js)

    return js_list


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
        locator_chain.append(f'js={js}')
    return locator_chain


def tp_click(driver: webdriver.Chrome, element: WebElement, **opt):
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


def js_get(driver: webdriver.Chrome, element: WebElement, key: str, **opt):
    # https: // selenium - python.readthedocs.io / api.html  # module-selenium.webdriver.remote.webelement
    # element has no info about driver, therefore, we need two args there

    js = js_by_key.get(key, None)

    if js is None:
        raise RuntimeError(f'key="key" is not supported')

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


def js_print(driver: webdriver.Chrome, element: WebElement, key: str, **opt):
    print(f"{key}={pformat(js_get(driver, element, key))}")


def js_print_debug(driver: webdriver.Chrome, element: WebElement, **opt):
    keys = ["attrs", "xpath"]
    print("specified element")
    for key in keys:
        js_print(driver, element, key)
    print(f"tpdata = {pformat(getattr(element, 'tpdata', None))}")
    print("active element")
    active_element = driver.switch_to.active_element
    for key in keys:
        js_print(driver, active_element, key)
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
    # ends up with many zombie webdriver running in the background.
    # therefore, we close the driver explicitly.
    driver.quit()
    # driver.dispose()    # this will call driver.close()

    my_env = tpsup.envtools.Env()
    # list all the log files for debug purpose
    # use double quotes to close "C:/Users/.../selenium*" because bare / is a switch in cmd.exe.
    cmd = f"{my_env.ls_cmd} -ld \"{driverEnv.log_base}/\"seleninum*"
    print(cmd)
    os.system(cmd)


def test_actions():
    my_env = tpsup.envtools.Env()
    url = None
    if my_env.isLinux:
        url = f'file:///{os.environ["TPSUP"]}/scripts/tpslnm_test_input.html'
    elif my_env.isWindows:
        url = f'file:///{os.environ["TPSUP"]}/scripts/tpslnm_test_input.html'
    else:
        raise RuntimeError("unsupport env")

    actions = [
        # ['url=https://google.com', 'tab=5'],
        # ['url=https://www.google.com'],
        # ['xpath=//input[@name="q"]', 'string=perl selenim'],
        [f"url={url}"],
        [
            'xpath=//input[@id="user id"],'
            "css=#user\ id,"
            'xpath=//tr[class="non exist"]',
            ["click", "debug", "sleep=3"],
            "go to user id",
        ],
        [
            "tab=4",
            ["debug", "sleep=3"],
            "go to Date of Birth",
        ],
        [
            "shifttab=3",
            ["click", "debug", "sleep=3"],
            "go back to password",
        ],
    ]

    print(f"test actions = {pformat(actions)}")

    driver = get_driver(host_port="localhost:19999")
    run_actions(driver, actions)

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

    interval = 5
    print(f"sleep {interval} seconds in case you want to Control-C")
    time.sleep(interval)

    driver.quit()


def follow(driver: Union[webdriver.Chrome, None],  steps: list, **opt):
    if not list:
        return

    dryrun = opt.get("dryrun", 0)
    interactive = opt.get("interactive", 0)
    debug = opt.get("debug", 0)
    verbose = opt.get("verbose", 0)
    checkonly = opt.get("checkonly", 0)
    if checkonly:
        dryrun = 1
    global we_return
    global action_data

    element: WebElement = None

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

        if m := re.match(r"\s*(while|if)(_not)?=(.+)", step):
            blockstart = m.group(1)
            negation = m.group(2)
            condition = m.group(3)

            if m := re.match(r"\s*(xpath|css|id)=(.+)", condition):
                tag, value, *_ = m.groups()
                if tag == 'id':
                    condition = f"driver.find_element(By.ID, '''{value}''')"
                elif tag == 'xpath':
                    if checkonly:
                        print(f"check xpath={value}")
                        try:
                            lxml.etree.XPath(value)
                        except lxml.etree.XPathSyntaxError as e:
                            raise RuntimeError(
                                f"XPath syntax error in step={step}: {e}")
                    condition = f"driver.find_element(By.XPATH, '''{value}''')"
                elif tag == 'css':
                    condition = f"driver.find_element(By.CSS_SELECTOR, '''{value}''')"

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
                    element = driver.find_element(By.ID, value)
                elif tag == 'xpath':
                    element = driver.find_element(By.XPATH, value)
                elif tag == 'css':
                    element = driver.find_element(By.CSS_SELECTOR, value)
        elif m := re.match(r"sleep=(\d+)", step):
            value, *_ = m.groups()
            print(f"follow(): sleep {value} seconds")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                time.sleep(int(value))
        elif m := re.match(r"wait=(\d+)", step):
            # implicit wait
            value, *_ = m.groups()
            print(f"follow(): set implicit wait {value} seconds")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                driver.implicitly_wait(int(value))
        elif m := re.match(r"key=(.+?),(\d+)", step, re.IGNORECASE):
            key, count_str = m.groups()
            count = int(count_str)
            print(f"follow(): type {key} {count} times")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                element.send_keys(Keys.__getattribute__(
                    Keys, key.upper()) * count)
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
        elif step == 'click':
            print(f"follow(): click")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                element.click()
        elif step == 'refresh':
            print(f"follow(): refresh driver")
            if interactive:
                hit_enter_to_continue(helper=helper)
            if not dryrun:
                driver.refresh()
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
        'page_load_timeout': {
            "switches": ["-plt", "-page_load_timeout"],
            "default": 15,
            "action": "store",
            "type": int,
            "help": "page load timeout in seconds. default to 15. "
            "For slow app like Service Now, we need set 30 or more. "
            "Even after page is loaded, it took more time for page to render fully; "
            "therefore, we need to add extra sleep time after page is loaded. "
            "implicitly_wait is set in 'wait=int' keyvaule",
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
    test_actions()


if __name__ == "__main__":
    main()
