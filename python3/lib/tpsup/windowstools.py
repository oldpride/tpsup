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

def is_window_winTypes(w: WindowSpecification, winTypes:str):
    cls = (w.class_name() or "").lower()
    # print(f"cls={cls}")
    # title = (w.window_text() or "").lower()
    cls = (w.class_name() or "").lower()
    # print(f"cls={cls}")
    # title = (w.window_text() or "").lower()

    winTypes = winTypes.lower().split(',')
    
    for wt in winTypes:
        # normalize winType for batch/cmd windows
        if wt in ("batch", "bat", "cmd"):
            wt = "CASCADIA_HOSTING_WINDOW_CLASS".lower()

        if wt == cls:
            return True

        # cygwin and gitbash needs special handling
        if wt in ("cyg", "cygwin", "git", "gitbash"):         
            # cygwin and gitbash use mintty
            if "mintty" != cls:
                continue

            if wt in ("git", "gitbash"):
                exe_pattern = "git"
            else:
                exe_pattern = "cygwin"
        
            # we need to use executable to distinguish between cygwin and gitbash.
            pid = w.process_id()
            import psutil

            p = psutil.Process(pid)

            print("exe:", p.exe())
            # batch cmd.exe: C:\Program Files\WindowsApps\Microsoft.WindowsTerminal_1.24.11911.0_x64__8wekyb3d8bbwe\WindowsTerminal.exe
            # cygwin mintty: C:\cygwin64\bin\mintty.exe
            # git bash mintty: C:\Program Files\Git\usr\bin\mintty.exe
        
            if exe_pattern in p.exe().lower():
                return True
            continue
        
    return False
