@echo off

setlocal EnableDelayedExpansion
set "prog=%~n0"

REM batch script doesn't have a $# equivalent. the following script is the best so far
set argC=0
for %%x in (%*) do Set /A argC+=1
rem echo %argC%

if NOT %argC% == 1 (
   echo ERROR:   wrong number of args. got %argC%, expected 1. args=%*
:usage
   echo usage:   %prog%  check
   echo          %prog%  set
   echo.
   echo          check or set vs code path
   echo.
   echo example: %prog%  check
   echo          %prog%  set
   exit /b
)

set var=%1

set "BASE=C:\Program Files\Microsoft VS Code"

if %var% == check (
   echo checking vs code installation, under expected %BASE%
   dir /b /a "%BASE%\Code.exe" && echo Found
   echo.

   echo checking vs code in PATH
   call which code
   exit /b
)

if NOT %var% == set (
   echo unknown action: %var%
   goto :usage
)

endlocal  & (
   if %var% == set (
      call addpath.cmd -p PATH "%BASE%"
      call which code
   )
)

