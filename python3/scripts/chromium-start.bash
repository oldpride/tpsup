#!/bin/bash
set -x
chromium-browser --no-sandbox --disable-dev_shm-usage -window-size=960,540 --user-data-dir=/tmp/selenium_chrome_browser_dir --remote-debugging-port=19999
