@echo off
REM is for comment
REM @ is to turn off echo
REM echo. is to print a new line

call addpath PYTHONPATH %TPSUP%\python3\lib
call addpath PYTHONPATH %SITEBASE%\Windows\Win10-Python3.7\lib\site-packages
echo. PYTHONPATH=%PYTHONPATH%
echo.
call addpath PATH %TPSUP%\python3\scripts
call addpath PATH %SITEBASE%\Windows\Win10-Python3.7\scripts
echo. PATH=%PATH%
echo.
echo Python is
where python
