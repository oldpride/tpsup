@echo off
REM is for comment
REM @ is to turn off echo
REM echo. is to print a new line

call addpath -q PYTHONPATH "%TPSUP%\python3\lib"
call addpath -q PYTHONPATH "%SITESPEC%\python3\lib"
if defined TP_P3_PYTHONPATH (
   call addpath -p -q PYTHONPATH "%TP_P3_PYTHONPATH%"
) else ( 
   echo. INFO: TP_P3_PYTHONPATH is not defined
)

echo. PYTHONPATH=%PYTHONPATH%
echo.

call addpath -q PATH "%TPSUP%\python3\scripts"
call addpath -q PATH "%SITESPEC%\python3\scripts"
if defined TP_P3_PATH (
   call addpath -p -q PATH "%TP_P3_PATH%"
) else (
   echo. INFO: TP_P3_PATH is not defined
)

echo. PATH=%PATH%
echo.

echo Python is
where python
python --version
