:: reset appium server for this error
:: UnknownError: An unknown server-side error occurred while processing the command. Original error: Could not proxy command to the remote server. Original error: socket hang up

call pkill.cmd node.exe
call adb.exe uninstall io.appium.uiautomator2.server
call adb.exe uninstall io.appium.uiautomator2.server.test

