@echo off

for /f %%i in ('C:\cygwin64\bin\cygpath.exe -w "/tmp"') do set "CYGTMP=%%i"
set "USER_TMP=%CYGTMP%\tmp_%USERNAME%"
@mycd "%USER_TMP%"
