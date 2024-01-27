@echo off

setlocal EnableDelayedExpansion

REM batch script doesn't have a $# equivalent. the following script is the best so far
set argC=0
for %%x in (%*) do Set /A argC+=1
rem echo %argC%


if NOT %argC% == 1 (
   echo ERROR:   wrong number of args. got %argC%, expected 1. args=%*
   echo usage:   %prog% mode
   echo.
   echo example: %prog% alltime
   echo          %prog% worktime
   echo          %prog% 10
   exit /b
)

endlocal

REM check whether i am already in venv
if defined VIRTUAL_ENV (
    echo INFO:   already in venv %VIRTUAL_ENV%
) else  (
    call p3env
    call svenv
)
@cscript "%TPSUP%/vbs/screenalive2.vbs" %*
call dvenv