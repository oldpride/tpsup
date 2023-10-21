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

@cscript "%TPSUP%/vbs/screenalive.vbs" %*