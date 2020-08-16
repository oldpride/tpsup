import os
import re
import sys
import time
from urllib.parse import urlparse
from shutil import which
import tpsup.env
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webelement import WebElement
from tpsup.nettools import is_tcp_open
import tpsup.pstools
import tpsup.tptmp
import os.path
from bs4 import BeautifulSoup
from tpsup.util import tplog


# +----------+      +--------------+     +----------------+
# | selenium +----->+ chromedriver +---->+ chrome browser +---->internet
# +----------+      +--------------+     +----------------+


class SeleniumEnv:
    def __init__(self, host_port: str, page_load_timeout:int = 15, **opt):
        global cmd
        (self.host, self.port) = host_port.split(':', 1)
        self.verbose = opt.get('verbose', 0)
        self.env = tpsup.env.Env()
        self.env.adapt()
        home_dir = self.env.home_dir
        system = self.env.system

        self.page_load_timeout = page_load_timeout

        self.dryrun = opt.get('dryrun', False)
        self.driverlog = home_dir + '/selenium_chromedriver.log'
        self.chromedir = home_dir + '/selenium_chrome_test'
        # driver log on Windows must use Windows path, eg, C:/Users/tian/test.log.
        # Even when we run the script from Cygwin or GitBash, we still need to use Windows path.

        # selenium will always start a chromedriver locally.
        # For Linux
        #     chromedriver should be in the path or at ~
        #     chromium-browser path is hard-coded in chromedriver
        #
        # For Windows,
        #     chromedriver.exe should be in the PATH or at C:/users/<username>
        #     chrome.exe       C:/Program Files (x86)/Google/Chrome/Application, hardcoded in chromedriver

        # self.download_dir = f"{self.env.home_dir}/Downloads/seleniumtools"
        download_dir = tpsup.tptmp.tptmp(base=f"{self.env.home_dir}/Downloads/selenium").get_nowdir(suffix='selenium')
        self.download_dir = self.env.adjpath(download_dir)

        self.headless = opt.get('headless', False)
        self.driver_exe = opt.get('driver', 'chromedriver')

        os.environ["PATH"] += os.pathsep + os.pathsep.join([home_dir])
        # chromedriver remembers chrome.exe's path, therefore, we don't need to set it
        if self.env.isWindows:
            # add home_dir and chrome.exe's path
            os.environ["PATH"] += os.pathsep + os.pathsep.join([f'C:/Users/{os.environ["USERNAME"]}',
                                                                r'C:\Program Files (x86)\Google\Chrome\Application'])
        if not re.search('[\\/]', self.driver_exe):
            # no path specified, then we are totally rely on $PATH
            path = which(self.driver_exe)
            if path is None:
                raise Exception(f'cannot find {self.driver_exe} in {os.environ["PATH"]}\n')
        else:
            # if path is specified, make sure it exist
            if not os.path.isfile(self.driver_exe):
                raise Exception(f'cannot find {self.driver_exe} not found. pwd={os.getcwd()}\n')

        self.driver_args = ["--verbose", f"--log-path={self.driverlog}"]  # for chromedriver

        if self.verbose:
            # print(sys.path)
            sys.stderr.write(f'pwd={os.getcwd()}\n')
            sys.stderr.write(f'PATH={os.environ["PATH"]}\n')

            self.print_running_drivers()

            if self.verbose > 1:
                if self.env.isLinux or self.env.isGitBash or self.env.isCygwin:
                    # display the beginning of the log file as 'tail' only display the later part
                    # use /dev/null to avoid error message in case the log file has not been created
                    cmd = f"cat /dev/null {self.driverlog}"
                    sys.stderr.write(cmd)
                    os.system(cmd)

                    # --pid PID  exits when PID is gone
                    # -F         retry file if it doesn't exist
                    cmd = f"tail --pid {os.getpid()} -F -f {self.driverlog} &"
                    sys.stderr.write(cmd)
                    os.system(cmd)
                elif self.env.isWindows:
                    # windows doesn't have a way to do "tail -f file &"
                    # 1. from cmd.exe, we would have to call powershell to use "tail -f" equivalent, but will
                    #    have difficulty to make the process background.
                    # https://stackoverflow.com/questions/185575/powershell-equivalent-of-bash-ampersand-for-forking-running-background-proce
                    # https://stackoverflow.com/questions/187587/a-windows-equivalent-of-the-unix-tail-command
                    # powershell.exe start-job -ScriptBlock { get-content C:/users/william/selenium_chromedriver.log -wait -tail 1 }
                    #
                    # 2. from powershell, Start-Job can easily run a ScriptBlock in background, but the output will
                    #    not come back to foreground.
                    # https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.core/start-job?view=powershell-7#:~:text=The%20Start%2DJob%20cmdlet%20starts,an%20extended%20time%20to%20finish.
                    # start-job -ScriptBlock { get-content C:/users/william/selenium_chromedriver.log -wait -tail 1 }
                    pass

        # chrome_options will be used on chrome browser's command line not chromedriver's commandline
        self.browser_options = Options()

        # try to connect the browser in case already exists.
        # by setting this, we tell chromedriver not to start a browser
        self.browser_options.debugger_address = f"{host_port}"

        self.driver = None
        sys.stderr.write(f'check browser port at {host_port}\n')
        self.connected_existing_browser = False
        if is_tcp_open(self.host, self.port):
            sys.stderr.write(f'{host_port} is open. let chromedriver to connect to it\n')
            if self.dryrun:
                sys.stderr.write(f'this is dryrun; we will not start chromedriver\n')
            else:
                try:
                    self.driver = webdriver.Chrome(self.driver_exe, options=self.browser_options,
                                                   service_args=self.driver_args)
                    sys.stderr.write(f'chromedriver has connected to chrome at {host_port}\n')
                    self.connected_existing_browser = True
                except Exception as e:
                    print(e)
        else:
            sys.stderr.write(f'{host_port} is not open.\n')

        if self.driver is None:
            # by doing one of the following, we tell chromedriver to start a browser
            # self.browser_options.debugger_address = None
            self.browser_options = Options()  # reset the browser options

            if self.host.lower() != 'localhost' and self.host != '127.0.0.1' and self.host != '':
                if self.dryrun:
                    sys.stderr.write("cannot connect to remote browser, but this is dryrun, so we continue\n")
                else:
                    raise RuntimeError("cannot connect to remote browser.")
            else:
                sys.stderr.write("cannot connect local browser. we will start it up")
                if self.headless:
                    self.browser_options.add_argument("--headless")
                    sys.stderr.write(" in headless mode\n")
                else:
                    sys.stderr.write("\n")

            if self.env.isLinux:
                self.browser_options.add_argument('--no-sandbox')  # to be able to run without root
                self.browser_options.add_argument('--disable-dev_shm-usage')  # to be able to run without root

            if self.env.isCygwin and self.headless:
                # some how only in Cygwin and only in headless mode, selenium needs --user-data-dir to use \, not /
                # C:\Users\william\selenium_chrome_test vs C:/Users/william/selenium_chrome_test
                self.browser_options.add_argument(f'--user-data-dir={self.chromedir}'.replace('/', r'\''))
            else:
                self.browser_options.add_argument(f'--user-data-dir={self.chromedir}')

            self.browser_options.add_argument('--window-size=960,540')
            self.browser_options.add_argument(f'--remote-debugging-port={self.port}')
            # browser_options.add_argument(f'--remote-debugging-address=127.0.0.1')

            # for file download
            self.browser_options.add_experimental_option("prefs", {
                "download.default_directory": self.download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            })

            for arg in opt.get('browserArgs', []):
                self.browser_options.add_argument(f'--{arg}')
                # chrome_options.add_argument('--proxy-pac-url=http://pac.abc.net')  # to run with proxy
            if self.dryrun:
                sys.stderr.write("this is dryrun, therefore, we don't start a webdriver, nor a browser\n")
            else:
                self.driver = webdriver.Chrome(self.driver_exe,  # make sure chromedriver is in the PATH
                                               options=self.browser_options,  # for chrome browser
                                               service_args=self.driver_args,  # for chromedriver
                                               )
                sys.stderr.write('started\n')
                # if self.headless:
                #    time.sleep(1)  # throttle for the headless mode

                # set timeout
                # https://stackoverflow.com/questions/17533024/how-to-set-selenium-python-webdriver-default-timeout
                self.driver.set_page_load_timeout(self.page_load_timeout)   # for chromedriver.
                # other driver use implicitly_wait()

    def get_driver(self):
        return self.driver

    def delay_for_viewer(self, seconds: int = 1):
        if not self.headless:
            time.sleep(seconds)  # Let the user actually see something!

    def quit(self):
        if self.driver is not None:
            self.driver.quit()
            self.driver = None

    def print_running_drivers(self):
        driver_basename = os.path.basename(self.driver_exe)
        tpsup.pstools.ps_grep_basename(driver_basename, env=self.env, verbose=self.verbose)

    def get_attrs(self, element: WebElement, method:str = 'bs4', verbose:int=0):
        """
        get list of attributes from an element.
        https://stackoverflow.com/questions/27307131/selenium-webdriver-how-do-i-find-all-of-an-elements-attributes
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
        if method == 'bs4':
            html: str = element.get_attribute('outerHTML')
            if verbose:
                tplog(f"outerHTML={html}")
            if html:
                attrs = {}
                soup = BeautifulSoup(html, 'html.parser')
                # https://www.crummy.com/software/BeautifulSoup/bs4/doc/#attributes
                for element in soup():
                    # soup() is a generator
                    # element.attrs is a dict
                    attrs.update(element.attrs)
                return attrs
            else:
                return {}
        elif method == 'js':
            # java script. duplicate attributes will be overwritten
            js_script = 'var items = {}; ' \
                        'for (index = 0; index < arguments[0].attributes.length; ++index) { ' \
                        '   items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value' \
                        '};' \
                        'return items;'
            attrs = self.driver.execute_script(js_script, element)
            return attrs
        else:
            raise RuntimeError(f"unsupported method={method}. accepted: bs4 or js")

def main():
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

    seleniumEnv = SeleniumEnv("localhost:19999", verbose=1)
    driver = seleniumEnv.get_driver()
    print(f'driver.title={driver.title}')

    url = 'http://www.google.com/'
    driver.get(url)
    try:
        # https://dev.to/endtest/a-practical-guide-for-finding-elements-with-selenium-4djf
        # in chrome browser, find the interested spot, right click -> inspect, this will bring up source code,
        # in the source code window, right click -> copy -> ...
        search_box = driver.find_element_by_name('q')
    except NoSuchElementException as e:
        print(e)
    else:
        search_box.clear()
        search_box.send_keys('ChromeDriver')

        # the following are the same
        # search_box.send_keys(webdriver.common.keys.Keys.RETURN)
        search_box.submit()
        seleniumEnv.delay_for_viewer()  # Let the user actually see something!

    for tag_a in driver.find_elements_by_tag_name('a'):
        link = None
        try:
            url = tag_a.get_attribute('href')
        # except NoSuchElementException as e:
        except NoSuchElementException:
            pass
        else:
            # print(f'url={url}')
            print(f'hostname = {urlparse(url).hostname}')

    # Selenium has no way to allow you start a webdriver and browser but only close the webdriver later.
    # When a webdriver starts a browser, it registers the closing action.
    # If we want to keep a browser running, we need to start it manually first, and then let the webdriver
    # to connect to it. As the webdriver didn't start the browser, it wouldn't register the closing action.
    # There were folks played with the code to only closing the webdriver without closing the browser, but
    # ends up with many zombie webdriver running in the background.
    # therefore, we close the driver explicitly.
    driver.quit()
    # driver.dispose()    # this will call driver.close()

    my_env = tpsup.env.Env()
    # list all the log files for debug purpose
    os.system(f"{my_env.ls} -ld {seleniumEnv.driverlog}")
    if my_env.isLinux:
        os.system(f"{my_env.ls} -ld {seleniumEnv.chromedir}")


if __name__ == '__main__':
    main()
