#!/usr/bin/env python

import argparse
import sys
import textwrap
from pprint import pformat
# from inspect import currentframe, getframeinfo
import os
import time
# import imported
from typing import List

import tpsup.pidfile
# from tpsup.util import tplog
from tpsup.logtools import get_logger

logger = get_logger()
prog = os.path.basename(sys.argv[0])

imported = None

# https://stackoverflow.com/questions/61324536/python-argparse-with-argumentdefaultshelpformatter-and-rawtexthelpformatter


class RawTextArgumentDefaultsHelpFormatter(argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    pass

# https://docs.python.o


def main():
    usage = textwrap.dedent(f"""
        keep screen alive on windows
        
        only works on windows
           pyautogui can run on linux but cannot move mouse
           pydirectinput and ctypes cannot even be imported on linux
           
        on linux, to test compile
           {prog} -v -m pyautogui 5
        """)

    examples = textwrap.dedent(f""" 
    examples:
        # 2 minutes
        {prog} 120
        
        {prog} -a presskey -a movemouse -a setstate -v 120 # only works on Windows
        
        """)

    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description=usage,
        # formatter_class=argparse.RawDescriptionHelpFormatter, # this keeps the format but doesn't print default value
        # formatter_class=argparse.ArgumentDefaultsHelpFormatter, # this disregard format but prints default value
        formatter_class=RawTextArgumentDefaultsHelpFormatter,  # this does both
        epilog=examples)

    parser.add_argument(
        'interval', default=-1, type=int,
        help="keep alive interval, in seconds, a positive integer")

    parser.add_argument(
        '-m', '--module', default="pydirectinput", choices=['pydirectinout', 'pyautogui'], type=str,
        help="choose a module.")

    parser.add_argument(
        '-a', '--action', default=["presskey"], choices=['presskey', 'movemouse', 'setstate'], action='append',
        help="choose a action.")

    parser.add_argument(
        '-v', '--verbose', default=0, action="count",
        help='verbose level: -v, -vv, -vvv')

    args = vars(parser.parse_args())

    verbose = args['verbose']
    interval = args['interval']
    module = args['module']
    actions = args['action']

    global imported
    imported = __import__(module)

    if verbose:
        sys.stderr.write(f"args =\n{pformat(args)}\n")
        logger.setLevel(level='DEBUG')

    if interval <= 0:
        parser.print_help(file=sys.stderr)
        sys.exit(1)

    interval = args['interval']

    # 0,0       X increases -->
    # +---------------------------+
    # |                           | Y increases
    # |                           |     |
    # |   1920 x 1080 screen      |     |
    # |                           |     V
    # |                           |
    # |                           |
    # +---------------------------+ 1919, 1079

    with tpsup.pidfile.pidfile(prog):
        # we use mouse movement to detect activity. this may not be perfect but should be good enough
        old_mX, old_mY = imported.position()  # mouse position

        logger.debug(f"mouse is at ({old_mX}, {old_mY})")

        while True:
            logger.debug(f"sleep {interval} sec")
            time.sleep(interval)

            mX, mY = imported.position()
            logger.debug(f"mouse is at ({mX}, {mY})")

            if mX == old_mX and mY == old_mY:
                # user idle
                logger.debug(f"user idle for {interval} seconds")
                take_actions(actions, X=mX, Y=mY)

            else:
                # user not idle, then not to interfere
                logger.debug(f"user active")

                old_mX, old_mY = mX, mY
                X0, Y0 = mX, mY


def take_actions(actions: List[str], **opt):
    old_mX = opt.get('X')
    old_mY = opt.get('Y')

    mX, mY = old_mX, old_mY
    for action in (actions):
        # moving mouse is not enough to keep screen from being locked, has to use key press
        # https://stackoverflow.com/questions/58273482/can-pyautogui-be-used-to-prevent-windows-screen-lock
        if action == 'movemouse':
            move = 100
            if mX > move:
                mX -= move
            else:
                mX += move
            if mY > move:
                mY -= move
            else:
                mY += move

            logger.debug(f"mv mouse to ({mX}, {mY})")
            # (X, Y, Duration) Duration minimum 0.1 second
            imported.moveTo(mX, mY, 1)
            time.sleep(1)
            logger.debug(f"mv mouse back to ({old_mX}, {old_mY})")
            imported.moveTo(old_mX, old_mY, 1)  # move back
        elif action == 'presskey':
            logger.debug(f"presss volumedown")
            imported.press('volumedown')
            time.sleep(1)
            logger.debug(f"press volumeup")
            imported.press('volumeup')
        elif action == 'setstate':
            if 'ctypes' not in sys.modules:
                import ctypes
            # https://docs.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate
            # ES_CONTINUOUS 0x80000000
            #    Informs the system that the state being set should remain in effect until the next call that uses ES_CONTINUOUS and one of the other state flags is cleared.
            # ES_DISPLAY_REQUIRED 0x00000002
            #    Forces the display to be on by resetting the display idle timer.
            logger.debug(f"SetThreadExecutionState(0x80000002)")
            ctypes.windll.kernel32.SetThreadExecutionState(
                0x80000002)  # 0x80000000 + 0x00000002
            time.sleep(1)
            logger.debug(f"SetThreadExecutionState(0x80000000)")
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == '__main__':
    main()
