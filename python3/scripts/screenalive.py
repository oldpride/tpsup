#!/usr/bin/env python

import argparse
import sys
import textwrap
from pprint import pformat
from inspect import currentframe, getframeinfo
import os
import time
import pyautogui
import tpsup.pidfile

prog = os.path.basename(sys.argv[0])

# https://docs.python.o
def main():
    usage = textwrap.dedent(""""\
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

    if interval <= 0 :
        parser.print_help(file=sys.stderr)
        sys.exit(1)

    interval = args['interval']

    with tpsup.pidfile.pidfile(prog) as pf:
        old_mX, old_mY = pyautogui.position() # mouse position

        if verbose:
            print(f"mouse is at ({old_mX}, {old_mY})", file=sys.stderr)

        # save a reference point as where we started
        X0, Y0 = old_mX, old_mY

        while(True):
            time.sleep(interval)
            mX, mY = pyautogui.position()
            if verbose:
                print(f"mouse is at ({mX}, {mY})", file=sys.stderr)

            if mX == old_mX and mY == old_mY:
                # user idle
                if mX > X0:
                    mX -= 1
                else:
                    mX += 1
                if mY > Y0:
                    mY -= 1
                else:
                    mY += 1

                if verbose:
                    print(f"mv mouse to ({mX}, {mY})", file=sys.stderr)
                pyautogui.move(mX, mY)
                old_mX = mX
                old_mY = mY
            else:
                # user not idle, then not to interfere
                old_mX, old_mY = pyautogui.position()
                X0, Y0 = old_mX, old_mY


if __name__ == '__main__':
    main()
