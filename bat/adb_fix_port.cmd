@echo off
setlocal
:: check number of command line arguments
if "%1"=="" (
    echo "Usage: adb_fix_port.cmd <new_port>"
    echo "Example: adb_fix_port.cmd 5555"
    exit /b 1
)

:: get first command line argument
set "new_port=%1"

:: $ adb devices
:: List of devices attached
:: 192.168.1.67:5555       device

:: get command output and set to variable
:: ^ means escape character
:: /v means exclude
for /f %%i in ('adb devices ^| grep device ^| grep /v devices') do (
    set "output=%%i"
)

:: check output is empty or not
if "%output%"=="" (
    echo "No device found connected to adb"
    exit /b 1
)

:: get ip:port from output 
for /f "tokens=1 delims= " %%a in ("%output%") do (
    set "ip_port=%%a"
)

echo ip_port=%ip_port%

FOR /f "tokens=1,2 delims=:" %%a IN ("%ip_port%") do (
    set ip=%%a& set old_port=%%b
)

echo %ip% 
echo %old_port%

adb tcpip %new_port%
adb kill-server
adb start-server
adb connect %ip%:%new_port%

endlocal