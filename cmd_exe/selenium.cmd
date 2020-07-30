@echo off
REM set up selenium test env
REM @ is to turn off echo
REM echo. is to print a new line

call addpath PATH %userprofile%

rem add path cannot handle space and () in file name yet
set "PATH=%PATH%;C:\Program Files (x86)\Google\Chrome\Application"

where chrome
where chromedriver
echo.
