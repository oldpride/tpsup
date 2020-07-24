# print key

if ([console]::NumberLock) {
    $wsh = New-Object -ComObject WScript.Shell
    $wsh.SendKeys('{NUMLOCK}')
    Write-Host "your NumLock was ON. This would interfere with Control Key. We toggled it off"
}

Start-Sleep -Milliseconds 500
while ($host.ui.rawui.KeyAvailable) {
    Write-Host "found leftovers"
    $key = $Host.ui.rawui.ReadKey("NoEcho, IncludeKeyUp")
    #$key = $Host.UI.RawUI.ReadKey("IncludeKeyUp")
    $key | Select-Object
}

Write-Host "above were leftovers"

$charArrayList = New-Object System.Collections.ArrayList

while ($true) {
    while ($host.ui.rawui.KeyAvailable) {
        $key = $Host.ui.rawui.ReadKey("NoEcho, IncludeKeyUp")
        $key | Select-Object

        if ($key.virtualKeycode -eq 8) {
            # this is a backspace, remove the last element
            $length = $charArrayList.Count
            if ($length -gt 0) {
                $charArrayList.RemoveAt($length - 1)
            }
        } elseif ($key.virtualKeycode -eq 13) {
            # this is a 'return', print the current string and reset the array list 
            $string = -join $charArrayList
            Write-Host "$string (length $($string.length))"
            $charArrayList.Clear()
        } elseif (($key.ControlKeyState -eq "LeftCtrlPressed" -or $key.ControlKeyState -eq "RightCtrlPressed") -and
            ($key.virtualKeycode -eq 68 -or $key.virtualKeycode -eq 90)) {
            # this Ctrl-D or Ctrl-Z, return current string and exit
            $string = -join $charArrayList
            Write-Host -n "$string (length $($string.length))"
            exit 0
        } else {
            $charArrayList.Add($key.character) | Out-Null
        }
    }

    Start-Sleep -Milliseconds 500
}
