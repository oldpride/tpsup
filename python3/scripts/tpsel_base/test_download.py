import argparse
import os
import shutil
import sys
import time
from pprint import pformat
from typing import List

import tpsup.seleniumtools_old
from tpsup.utilbasic import tplog


def run(seleniumEnv: tpsup.seleniumtools_old.SeleniumEnv, **opt):
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

    url = f"https://metacpan.org/pod/DBI::Log"
    tplog(f"going to url={url}")

    driver.get(url)

    # https://stackoverflow.com/questions/46937319/how-to-use-chrome-webdriver-in-selenium-to-download-files-in-python
    driver.command_executor._commands["send_command"] = (
        "POST", '/session/$sessionId/chromium/send_command')
    params = {'cmd': 'Page.setDownloadBehavior',
              'params': {'behavior': 'allow', 'downloadPath': seleniumEnv.download_dir}}
    command_result = driver.execute("send_command", params)

    time.sleep(1)

    # https://dev.to/endtest/a-practical-guide-for-finding-elements-with-selenium-4djf
    download_text = 'Download ('
    elem = driver.find_element_by_partial_link_text(download_text)

    elem.click()
    tplog(f"clicked '{download_text}'")

    wait_time_for_download = float(args['wait'])
    time.sleep(wait_time_for_download)

    # control file name
    # https://stackoverflow.com/questions/34548041/selenium-give-file-name-when-downloading
    files: List[str] = [os.path.join(seleniumEnv.download_dir, f)
                        for f in os.listdir(seleniumEnv.download_dir)]
    if files:
        filename = max(files, key=os.path.getctime)
        renamed = args['renamed']
        if renamed:
            shutil.move(filename, os.path.join(
                seleniumEnv.download_dir, renamed))
            return renamed
        else:
            return filename
    else:
        tplog(f"no file downloaded to {seleniumEnv.download_dir}")
        raise RuntimeError(
            f"no file downloaded in {wait_time_for_download} seconds")
