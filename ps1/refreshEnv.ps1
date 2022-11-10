#requires -version 2
 
# update user env using setx or "settings->edit user env" normally requires a reboot or logout/login
# to have other programs to pick up the new change. running processes will not pick up the change.
# this script can "broadcast the WM_SETTINGCHANGE message", and therefore, avoid a reboot.
#    https://superuser.com/questions/387619
# script is at
#    http://web.archive.org/web/20170516120430/http://poshcode.org/2049
# a non-zero output means successful.
#

if (-not ("win32.nativemethods" -as [type])) {
    # import sendmessagetimeout from win32
    add-type -Namespace Win32 -Name NativeMethods -MemberDefinition @"
[DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
public static extern IntPtr SendMessageTimeout(
   IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam,
   uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);
"@
}
 
$HWND_BROADCAST = [intptr]0xffff;
$WM_SETTINGCHANGE = 0x1a;
$result = [uintptr]::zero
 
# notify all windows of environment block change
[win32.nativemethods]::SendMessageTimeout($HWND_BROADCAST, $WM_SETTINGCHANGE,
        [uintptr]::Zero, "Environment", 2, 5000, [ref]$result);
