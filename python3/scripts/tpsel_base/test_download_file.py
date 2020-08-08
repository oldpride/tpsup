import os
import re

import argparse
import shutil
import sys
import time
import urllib.request
from pprint import pformat
from inspect import currentframe, getframeinfo

import tpsup.seleniumtools
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from urllib.parse import urlparse
from tpsup.lock import EntryBook


def run(seleniumEnv: tpsup.seleniumtools.SeleniumEnv, **opt):
    username = "lca_editor"  # change this to the username associated with your account
    verbose = opt.get('verbose', 0)
    mod_file = opt.get('mod_file', 'mod_file')

    argList = opt.get('argList', [])
    args = None
    if verbose:
        sys.stderr.write(f"{mod_file} argList=\n")
        sys.stderr.write(pformat(argList) + "\n")
    if argList:
        parser = argparse.ArgumentParser(
            prog=mod_file,
        )
        parser.add_argument(
            '-js', dest='use_javascript', default=False, action='store_true',
            help='use javascript')

        parser.add_argument(
            '-wait', dest='wait', default=5, action='store', type=int,
            help='rename the file. default not to rename')

        parser.add_argument(
            '-rename', dest='renamed', default=None, action='store',
            help='rename the file. default not to rename')

        args = vars(parser.parse_args(argList))
        username=args['username']

    driver = seleniumEnv.get_driver()

    url = f"http://livingstonchinese.org/LCA2/index.php/join-us"
    driver.get(url)

    # https://stackoverflow.com/questions/46937319/how-to-use-chrome-webdriver-in-selenium-to-download-files-in-python
    driver.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')
    params = {'cmd': 'Page.setDownloadBehavior',
              'params': {'behavior': 'allow', 'downloadPath': seleniumEnv.download_dir}}
    command_result = driver.execute("send_command", params)


    # https://dev.to/endtest/a-practical-guide-for-finding-elements-with-selenium-4djf

    # <a style="color: #1b57b1; font-weight: normal; text-decoration: none;"
    # href="/LCA2/images/docs/public/lca_bylaw_2019_11.pdf">lick to view LCA By Law</a>
    #elem = driver.find_element_by_css_selector("#content > div.item-page > div:nth-child(4) > pre:nth-child(15) > span > a")
    elem = driver.find_element_by_partial_link_text("view LCA By Law")

    is_download_link = False
    if not is_download_link:
        src = elem.get_attribute("href")
        urllib.request.urlretrieve(src, f"{seleniumEnv.download_dir}/lca.pdf")
        return
    else:
        elem.click()
        time.sleep(float(args['wait']))

        # control file name
        # https://stackoverflow.com/questions/34548041/selenium-give-file-name-when-downloading
        filename = max([seleniumEnv.download_dir + "/" + f for f in os.listdir(seleniumEnv.download_dir)],
                       key=os.path.getctime)
        renamed = args['renamed']
        if renamed:
            shutil.move(filename, os.path.join(seleniumEnv.download_dir, renamed))
            return renamed
        else:
            return filename