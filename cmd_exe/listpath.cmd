@echo off

set "prog=%~n0"

setlocal EnableDelayedExpansion

REM batch script doesn't have a $# equivalent. the following script is the best so far
set argC=0
for %%x in (%*) do Set /A argC+=1
rem echo %argC%

if NOT %argC% == 1 (
   echo ERROR:   wrong number of args. got %argC%, expected 1. args=%*
   echo usage:   %prog% var_name 
   echo example: %prog% PATH 
   echo example: %prog% PATH  ^| sort
   echo example: %prog% PYTHONPATH 
   exit /b
)

set var=%1
set value=!%var%!

rem how to split %path% which is delimited by ;
rem https://stackoverflow.com/questions/14879105/windows-path-variable-how-to-split-on-in-cmd-shell-again
for %%i in ("%value:;="; "%") do (
   echo. %%~i 
)
endlocal
