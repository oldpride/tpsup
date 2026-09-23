import psutil
import pywinauto

from pywinauto.application import WindowSpecification

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

def is_window_termType(w: WindowSpecification, termType:str):
    cls = (w.class_name() or "").lower()
    # print(f"cls={cls}")
    # title = (w.window_text() or "").lower()
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

    print(f"termType={termType}, cls={cls}")
    
    if termType in ("cygwin", "git"):
        # cygwin and gitbash use mintty
        if "mintty" not in cls:
            return False
    elif termType in ("mintty", "putty"):
        if termType == cls:
            return True
        else:
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
