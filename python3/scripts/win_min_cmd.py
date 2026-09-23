#!/usr/bin/env python
import argparse
from pywinauto import Desktop
import psutil
from tpsup.windowstools import is_window_termType

def is_keep_window(w):
    cls = (w.class_name() or "").lower()
    title = (w.window_text() or "").strip()

    try:
        pid = w.process_id()
    except Exception:
        return False

    try:
        p = psutil.Process(pid)
        exe = (p.exe() or "").lower()
        cmd = " ".join(p.cmdline() or []).lower()
    except Exception:
        exe = ""
        cmd = ""

    # Keep PuTTY by executable or class name
    if "putty" in exe or "putty" in cmd or "putty" in cls:
        return True

    # Keep Cygwin Mintty by executable/class
    if "mintty" in cls and ("cygwin" in exe or "cygwin" in cmd):
        return True

    return False

def minimize_all_except_keep(verbose=False, dry_run=False):
    desktop = Desktop(backend="win32")
    minimized = []
    kept = []

    for w in desktop.windows():
        title = (w.window_text() or "").strip()
        if is_keep_window(w):
            kept.append(title)
            continue

        try:
            if verbose:
                print(f"minimizing: {title or w.class_name()} [{w.process_id()}]")

            if not dry_run:
                w.minimize()

            minimized.append(title or w.class_name())
        except Exception as e:
            print(f"failed to minimize {title or w.class_name()}: {e}")

    return minimized, kept

def main():
    parser = argparse.ArgumentParser(
        description="Minimize all windows except Cygwin and PuTTY."
    )
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print each window that is minimized")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be minimized without changing windows")
    args = parser.parse_args()

    minimized, kept = minimize_all_except_keep(
        verbose=args.verbose,
        dry_run=args.dry_run,
    )

    print(f"minimized: {len(minimized)}")
    print(f"kept: {len(kept)}")

    if args.verbose:
        for t in minimized:
            print(f"  - {t}")

if __name__ == "__main__":
    main()
