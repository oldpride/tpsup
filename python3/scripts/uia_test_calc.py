#!/usr/bin/env python

# usage: python pwa_test_calc.py

from subprocess import Popen
from pywinauto import Desktop
from time import sleep

Popen('calc.exe', shell = True)
dialog = Desktop(backend='uia').Calculator
dialog.wait('visible')
sleep(1)

print(f"dir(dialog) = {dir(dialog)}")
print(f"dialog.print_control_identifiers() = {dialog.print_control_identifiers()}")

dialog.Three.click()
dialog.Plus.click()
dialog.Four.click()
dialog.Equals.click()
sleep(2)

# we leave the calculator open
# dialog.close() # this will close the whole calculator app
