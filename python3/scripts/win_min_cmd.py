#!/usr/bin/env python
import argparse
import os
import sys

from pywinauto import Desktop
from tpsup.windowstools import is_window_winTypes


def process_winTypes(winTypes:str, excludeFlag=False, restoreFlag=False, verbose=False, dry_run=False):
    desktop = Desktop(backend="win32")
    windows = []

    if restoreFlag:
        action = "restoring"
    else:
        action = "minimizing"

    for w in desktop.windows():
        title = (w.window_text() or "").strip()
        cls = (w.class_name() or "").strip().lower()

        if is_window_winTypes(w, winTypes):
            if excludeFlag:
                continue
        else:
            if not excludeFlag:
                continue

        if restoreFlag:
            try:
                visible = bool(w.is_visible())
            except Exception:
                visible = False

            if not w.is_minimized():
                continue

            if not visible:
                # skip background windows that are not visible
                continue

            if dry_run:
                if verbose:
                    print(f"{action} (dry run): {cls} | {title or '<no title>'} [{w.process_id()}]")
                continue

            if verbose:
                print(f"{action}: {cls} | {title or '<no title>'} [{w.process_id()}]")
            try:
                w.restore()
            except Exception as e:
                print(f"failed to restore {cls} | {title or '<no title>'}: {e}", file=sys.stderr)
        else:
            # minimizing
            if not w.is_minimized():
                if dry_run:
                    if verbose:
                        print(f"{action} (dry run): {cls} | {title or '<no title>'} [{w.process_id()}]")
                    continue
                
                if verbose:
                    print(f"{action}: {cls} | {title or '<no title>'} [{w.process_id()}]")
                try:
                    w.minimize()
                except Exception as e:
                    print(f"failed to minimize {cls} | {title or '<no title>'}: {e}", file=sys.stderr)

            windows.append(w)

    return windows


def main():
    prog = os.path.basename(sys.argv[0])

    usage = f"""
usage:
    {prog} winTypes

    class_names include
    - all win class names: putty, mintty
    - and some custom names: cyg, gitbash, batch, cmd, bat
    - use lowercase for all class names

    examples:
      {prog} vscode,chrome
      {prog} -x putty,mintty
      {prog} -r vscode,chrome

    -v
    -x
    --dry-run
    -r/--restore
"""
    
    parser = argparse.ArgumentParser(
        description="Minimize all windows except those whose class names are listed."
    )
    parser.add_argument(
        "remainingArgs",
        nargs="*",
        help="Window types to minimize or restore, connected by commas, for example: vscode,chrome",
    )
    parser.add_argument(
        "-x", "--excludeFlag",
        action="store_true",
        default=False,
        help="Exclude windows with these class names from being minimized or restored",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print each window that is minimized or restored",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be minimized or restored without changing windows",
    )
    parser.add_argument(
        "-r", "--restore",
        action="store_true",
        help="Restore minimized windows to normal size instead of minimizing others",
    )

    args = parser.parse_args()

    if len(args.remainingArgs) != 1:
        print("wrong number of arguments", file=sys.stderr)
        print(usage, file=sys.stderr)
        sys.exit(1)

    termTypes = args.remainingArgs[0].split(",")

    windows = process_winTypes(
        termTypes=termTypes,
        excludeFlag=args.excludeFlag,
        restoreFlag=args.restore,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )

    print(f"processed: {len(windows)} windows")


if __name__ == "__main__":
    main()
