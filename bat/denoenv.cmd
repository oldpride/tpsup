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
   echo          check or set deno path
   echo.
   echo example: %prog%  check
   echo          %prog%  set
   exit /b
)

set var=%1

set "BASE=%USERPROFILE%\.deno\bin"

if %var% == check (
   echo checking deno installation, under expected %BASE%
   dir /b /a "%BASE%\file-server.cmd" && echo Found
   echo.

   echo checking deno file-server in PATH
   call which file-server
   exit /b
)

if NOT %var% == set (
   echo unknown action: %var%
   goto :usage
)

endlocal  & (
   if %var% == set (
      call addpath.cmd -p PATH "%BASE%"
      call which file-server
   )
)
