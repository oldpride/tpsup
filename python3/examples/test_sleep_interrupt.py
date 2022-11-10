#!/usr/bin/env python

# this was used to test a stackoverflow case
# https://stackoverflow.com/questions/63287063/python-script-in-git-bash-ignores-keyboard-interrupt-control-c
#
# When I run the script directly, Control C is ignored
#
# $ ./test_sleep_interrupt.py
# sleep #0
# sleep #1
# sleep #2
# (hitting Control-C many times, no effect)
# sleep #3
# sleep #4
# sleep #5
# sleep #6
# sleep #7
# sleep #8
# sleep #9
# When I run it through python, Control-C works immediately
#
# $ python ./test_sleep_interrupt.py
# sleep #0
# sleep #1
# (typed Control-C)
# Traceback (most recent call last):
#   File "./test_sleep_interrupt.py", line 5, in <module>
#     time.sleep(1)
# KeyboardInterrupt
#
# Following @ConnorLow's suggestion, I upgraded my Git for Windows to the latest version 2.28.0, which includes
# Git Bash mintty 3.2.0. This fixed the reported problem
import time
for i in range(0, 10):
    print(f"sleep #{i}")
    time.sleep(1)
