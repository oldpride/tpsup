#!/usr/bin/env python
import argparse
import re
import subprocess
import sys
from pywinauto import Desktop

def is_window_type(w, termType:str):
    cls = (w.class_name() or "").lower()
    # print(f"cls={cls}")
    # title = (w.window_text() or "").lower()

    termType = termType.lower()

    if termType in ("gitbash"):
        termType = "git"
    elif termType in ("cyg"):
        termType = "cygwin"
    elif termType in ("batch", "bat"):
        termType = "cmd"

    if termType in ("cygwin", "git"):
        # cygwin and gitbash use mintty
        if "mintty" not in cls:
            return False
    elif termType in ("cmd"):
        if "CASCADIA_HOSTING_WINDOW_CLASS".lower() in cls:
            return True
        return False
    else:
        raise ValueError(f"Unsupported termType: {termType}")

    if termType in ("cygwin", "git"):
        # we need to use executable to distinguish between cygwin and gitbash.
        pid = w.process_id()
        import psutil

        p = psutil.Process(pid)

        print("exe:", p.exe())
        # batch cmd.exe: C:\Program Files\WindowsApps\Microsoft.WindowsTerminal_1.24.11911.0_x64__8wekyb3d8bbwe\WindowsTerminal.exe
        # cygwin mintty: C:\cygwin64\bin\mintty.exe
        # git bash mintty: C:\Program Files\Git\usr\bin\mintty.exe
    
        if termType in p.exe().lower():
            return True
        return False
    else:
        raise RuntimeError(f"we should never be here. Unexpected termType: {termType}")
    
def get_external_monitor_resolution():
    import subprocess
    cmd = r"""
    Get-CimInstance Win32_VideoController |
    Where-Object {
        ($_.PNPDeviceID -like 'USB*' -or $_.PNPDeviceID -like 'SWD*') -and
        $_.MaxRefreshRate -ne $null -and
        $_.MinRefreshRate -ne $null
    } |
    Select-Object -ExpandProperty CurrentHorizontalResolution
    """

    print(f"cmd={cmd}")

    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True,
        text=True
    )
    
    print(f"result={result}")
    if result.returncode == 0:
        return int(result.stdout.strip())
    else:
        raise RuntimeError("cmd failed")


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
        if not is_window_type(w, termType):
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
    parser.add_argument("termType", type=str, choices=["cyg", "cygwin", "git", "gitbash","batch", "bat", "cmd"], help="Type of terminal window to move")
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
