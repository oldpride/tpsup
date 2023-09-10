#!/usr/bin/env python

import time
from appium import webdriver
from urllib.parse import urlparse

import argparse
import sys
import textwrap
from pprint import pformat
import os
import platform
import re

from appium.webdriver.common.appiumby import AppiumBy

import tpsup.envtools

prog = os.path.basename(sys.argv[0])

home_dir = os.path.expanduser("~")
uname = platform.uname()
system = uname.system


usage = textwrap.dedent(f"""   

    {prog} appium_server_host:port android_studio_device

    """)

examples = textwrap.dedent(f""" 
    1. start a device (real or emulator),
       from Android Studio (this step takes a long time) or from command line.   
           C:\\Users\william\AppData\Local\Android\Sdk\emulator\emulator -avd myemulator      
        run 'adb devices' to get the device name
    2. start Appium Server, note down the host and port. 
       this step takes a long time.
           appium --address localhost --port 4723 --log-no-colors --base-path /wd/hub      
    3. (optional) start Appium Inspector, use the desired capabilities in this script to connect
    4. run this script
        python {prog} localhost:4723 emulator-5554
    5. run uiautomatorviewer to inspect element
        C:\\Users\william\appdata\local\android\Sdk\tools\bin\\uiautomatorviewer
        click snapshot
    6. run Appium Inspector to inspect element
        "C:\Program Files\Appium Inspector\Appium Inspector.exe"
        set host/port/desired capability, then click start.
        by default, inspector only shows resource_id. 
        click "toggle attributes" button to see more attributes   

    """)

parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=usage,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    # formatter_class=argparse.RawTextHelpFormatter, # this honors \n but messed up indents
    epilog=examples)

parser.add_argument(
    '-v', '--verbose', default=0, action="count",
    help='verbose level: -v, -vv, -vvv')

parser.add_argument(
    'host_port', default=None,
    help="host:port of appium server. eg, 127.0.0.1:4723")

parser.add_argument(
    'device', default=None,
    help="android studio device. seen in 'adb devices'")


args = vars(parser.parse_args())

if args['verbose']:
    sys.stderr.write("args =\n")
    sys.stderr.write(pformat(args) + "\n")

desired_cap = {
    "appium:deviceName": args["device"],
    "appium:platformName": "Android"
}

# https://www.youtube.com/watch?v=h8vvUcLo0d0
driver = webdriver.Remote(f"http://{args['host_port']}/wd/hub", desired_cap)
driver.implicitly_wait(60)
print("driver started")

print(f"sleep 3 seconds")
time.sleep(3)

# https://appium.io/docs/en/commands/context/get-contexts/S
contexts = driver.contexts
print(f'available contexts = {pformat(contexts)}')

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
target_attr="content-desc"
elements = driver.find_elements(AppiumBy.XPATH, f"//*[@{target_attr}]") # attr existence
for e in elements:
    print(f"{e.get_attribute(target_attr)}")


interval = 5
print(f"sleep {interval} seconds")
time.sleep(interval)



print("quiting")
driver.quit()

exit(0)