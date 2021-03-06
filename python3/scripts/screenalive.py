#!/usr/bin/env python

import argparse
import sys
import textwrap
from pprint import pformat
# from inspect import currentframe, getframeinfo
import os
import time
import pyautogui
import tpsup.pidfile
# from tpsup.util import tplog
from tpsup.tplog import get_logger

logger = get_logger()
prog = os.path.basename(sys.argv[0])


# https://docs.python.o
def main():
    usage = textwrap.dedent(""""
        keep screen alive
        """)

    examples = textwrap.dedent(f""" 
    examples:
        # 2 minutes
        {prog} 120
        """)

    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description=usage,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples)

    parser.add_argument(
        'interval', default=-1, type=int,
        help="keep alive interval, in seconds, a positive integer")

    parser.add_argument(
        '-v', '--verbose', default=0, action="count",
        help='verbose level: -v, -vv, -vvv')

    args = vars(parser.parse_args())

    verbose = args['verbose']
    interval = args['interval']

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
        old_mX, old_mY = pyautogui.position()  # mouse position

        logger.debug(f"mouse is at ({old_mX}, {old_mY})")

        # save a reference point as where we started
        X0, Y0 = old_mX, old_mY

        while True:
            logger.debug(f"sleep {interval} sec")
            time.sleep(interval)
            mX, mY = pyautogui.position()
            logger.debug(f"mouse is at ({mX}, {mY})")

            if mX == old_mX and mY == old_mY:
                # user idle
                logger.debug(f"user idle")

                if mX > X0:
                    mX -= 1
                else:
                    mX += 1
                if mY > Y0:
                    mY -= 1
                else:
                    mY += 1

                logger.debug(f"mv mouse to ({mX}, {mY})")
                pyautogui.moveTo(mX, mY, 0.1)  # (X, Y, Duration) Duration minimum 0.1 second
                # pyautogui.move(delta_X, delta_Y)

                old_mX = mX
                old_mY = mY
            else:
                # user not idle, then not to interfere
                logger.debug(f"user active")

                old_mX, old_mY = mX, mY
                X0, Y0 = mX, mY


if __name__ == '__main__':
    main()
