#!/usr/bin/env python
import argparse
import os
import re
import subprocess
import sys
import textwrap
from pywinauto import Desktop
from tpsup.windowstools import is_window_termType, get_external_monitor_resolution


def move_all_termType_windows(termType, xy, byMonitor=False, verbose=False):
    if byMonitor:
        xy = float(xy)
        monitor_horizontal_resolution = get_external_monitor_resolution()
        print(f"Monitor horizontal resolution: {monitor_horizontal_resolution}")
        dx=int(monitor_horizontal_resolution*xy)
        dy=0
    else:
        # xy is in the format int,int
        dx, dy = map(int, xy.split(","))

    print(f"dx={dx}, dy={dy}")
        
    desktop = Desktop(backend="win32")
    moved = []

    for w in desktop.windows():
        if not is_window_termType(w, termType):
            continue

        try:
            w.restore()
        except Exception:
            pass

        r = w.rectangle()
        x = r.left
        y = r.top
        width = r.width()
        height = r.height()

        new_x = x + dx
        new_y = y + dy

        try:
            w.move_window(new_x, new_y, width, height)
            moved.append((w.window_text(), (x, y), (new_x, new_y)))
            if verbose:
                print(f"Moved: {w.window_text()} from {x},{y} to {new_x},{new_y}")
        except Exception as e:
            print(f"Failed to move {w.window_text()}: {e}")

    return moved

def main():
    prog = os.path.basename(sys.argv[0])
    usage = textwrap.dedent(""""\
        move all cygwin/gitbash/batch windows by x,y pixels.
        """)

    examples = textwrap.dedent(f""" 
        -v  # verbose mode
        -m  # move by monitor widthratio, 
            e.g., 0.5 for half the monitor width

    examples:
        # move all cygwin by 1920 pixels horizontally
        {prog} cyg "1920,0"

        # move them back
        {prog} cyg "-1920,0"

        # move all batch by half the monitor width
        {prog} batch -m 0.5

        # move them back
        {prog} batch -m -0.5 
        """)

    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description=usage,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=examples)

    # parser = argparse.ArgumentParser(
    #     description="Move all cygwin/gitbash/batch windows by x,y pixels."
    # )
    parser.add_argument("termType", type=str, choices=["cyg", "cygwin", "git", "gitbash","batch", "bat", "cmd", "putty", "mintty"], help="Type of terminal window to move")
    parser.add_argument("xy", type=str, help="Offset in the format 'dx,dy'")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print each moved window")
    parser.add_argument("-m", "--byMonitor", action="store_true", 
                        help="xy arg will be an float, jump this number of monitors away, can be negative or positive")
    args = parser.parse_args()

    results = move_all_termType_windows(args.termType, args.xy, byMonitor=args.byMonitor, verbose=args.verbose)
    print(f"Moved {len(results)} {args.termType} windows")
    if args.verbose:
        for title, old_pos, new_pos in results:
            print(f"{title}: {old_pos} -> {new_pos}")

if __name__ == "__main__":
    main()
