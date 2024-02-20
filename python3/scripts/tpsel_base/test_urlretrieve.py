import argparse
import sys
import urllib.request
from pprint import pformat

import tpsup.seleniumtools
from tpsup.utilbasic import tplog


def run(seleniumEnv: tpsup.seleniumtools.SeleniumEnv, **opt):
    verbose = opt.get('verbose', 0)
    mod_file = opt.get('mod_file', 'mod_file')

    argList = opt.get('argList', [])

    if verbose:
        sys.stderr.write(f"{mod_file} argList=\n")
        sys.stderr.write(pformat(argList) + "\n")

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

    if not verbose:
        verbose = args.get('verbose', 0)

    if verbose:
        tplog(f"args = {pformat(args)}")

    driver = seleniumEnv.get_driver()

    url = f"http://livingstonchinese.org/LCA2/index.php/join-us"
    driver.get(url)

    # https://stackoverflow.com/questions/46937319/how-to-use-chrome-webdriver-in-selenium-to-download-files-in-python
    driver.command_executor._commands["send_command"] = (
        "POST", '/session/$sessionId/chromium/send_command')
    params = {'cmd': 'Page.setDownloadBehavior',
              'params': {'behavior': 'allow', 'downloadPath': seleniumEnv.download_dir}}
    command_result = driver.execute("send_command", params)

    # https://dev.to/endtest/a-practical-guide-for-finding-elements-with-selenium-4djf

    # <a style="color: #1b57b1; font-weight: normal; text-decoration: none;"
    # href="/LCA2/images/docs/public/lca_bylaw_2019_11.pdf">lick to view LCA By Law</a>
    # elem = driver.find_element_by_css_selector("#content > div.item-page > div:nth-child(4) > pre:nth-child(15) > span > a")
    elem = driver.find_element_by_partial_link_text("view LCA By Law")

    src = elem.get_attribute("href")
    env = seleniumEnv.env
    download_dir = seleniumEnv.download_dir

    shortname = "lca.pdf"
    urllib.request.urlretrieve(src, f"{download_dir}/{shortname}")

    return download_dir
