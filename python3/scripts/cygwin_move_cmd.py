#!/usr/bin/env python
import argparse
import re
import sys
from pywinauto import Desktop

def is_cygwin_window(w):
    cls = (w.class_name() or "").lower()
    title = (w.window_text() or "").lower()
    return "mintty" in cls or "cygwin" in cls or "bash" in title

def get_external_monitor_resolution():
    import subprocess
    cmd = """powershell -Command 'Get-CimInstance Win32_VideoController | Where-Object { ($_.PNPDeviceID -like "USB*" -or $_.PNPDeviceID -like "SWD*") -and $_.MaxRefreshRate -ne $null -and $_.MinRefreshRate -ne $null } | Select-Object -ExpandProperty CurrentHorizontalResolution'"""
    print(f"cmd={cmd}")
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    print(f"result={result}")
    if result.returncode == 0:
        return int(result.stdout.strip())
    else:
        raise RuntimeError("cmd failed")
    return None


def move_all_cygwin_windows(xy, byMonitor=False, verbose=False):
    if byMonitor:
        xy = int(xy)
        monitor_horizontal_resolution = get_external_monitor_resolution()
        dx=monitor_horizontal_resolution
        dy=0
    else:
        # xy is in the format int,int
        dx, dy = map(int, xy.split(","))
        
    desktop = Desktop(backend="win32")
    moved = []

    for w in desktop.windows():
        if not is_cygwin_window(w):
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
    parser = argparse.ArgumentParser(
        description="Move all Cygwin/Mintty windows by DX and DY pixels."
    )
    parser.add_argument("xy", type=str, help="Offset in the format 'dx,dy'")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print each moved window")
    parser.add_argument("-m", "--byMonitor", action="store_true", 
                        help="xy arg will be an int, jump number of monitors away, can be negative or positive")
    args = parser.parse_args()

    results = move_all_cygwin_windows(args.xy, byMonitor=args.byMonitor, verbose=args.verbose)
    print(f"Moved {len(results)} Cygwin windows")
    if args.verbose:
        for title, old_pos, new_pos in results:
            print(f"{title}: {old_pos} -> {new_pos}")

if __name__ == "__main__":
    main()
