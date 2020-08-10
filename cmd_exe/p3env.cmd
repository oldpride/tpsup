@echo off
REM is for comment
REM @ is to turn off echo
REM echo. is to print a new line

rem set PYTHONPATH=%PYTHONPATH%;C:/users/%USERNAME%/github/tpsup/python3/lib
rem call addpath PYTHONPATH %userprofile%/sitebase/github/tpsup/python3/lib
call addpath PYTHONPATH %TPSUP%\python3\lib
echo. PYTHONPATH=%PYTHONPATH%
echo.
call addpath PATH %TPSUP%\python3\scripts
echo. PATH=%PATH%
echo.
echo Python is
where python
