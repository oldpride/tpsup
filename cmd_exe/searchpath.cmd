@echo off

set "prog=%~n0"

setlocal EnableDelayedExpansion

REM batch script doesn't have a $# equivalent. the following script is the best so far
set argC=0
for %%x in (%*) do Set /A argC+=1
rem echo %argC%

if NOT %argC% == 2 (
   echo ERROR:   wrong number of args. got %argC%, expected 1. args=%*
   echo usage:   %prog% var_name file
   echo example: %prog% PATH python 
   echo example: %prog% PATH grep
   echo example: %prog% PYTHONPATH tpsup
   exit /b
)

set var=%1
set file=%2
set value=!%var%!

rem assign command output to var
for /f %%i in ('where where') do set "where=%%i"

rem how to split %path% which is delimited by ;
rem https://stackoverflow.com/questions/14879105/windows-path-variable-how-to-split-on-in-cmd-shell-again
for %%i in ("%value:;="; "%") do (
   rem echo. %%~i 
   set "PATH=%%~i"

   rem redirect stderr to /dev/null
   %where% %file% 2> nul
)
endlocal
