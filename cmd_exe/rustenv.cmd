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
   echo          set or check rust and wasm env
   echo.
   echo example: %prog%  check
   echo          %prog%  set
   exit /b
)

set var=%1

set "CARGO_BASE=C:\Users\%USERNAME%\.cargo"
set "WABT_BASE=C:\Users\%USERNAME%\local\wabt-1.0.34"

if %var% == check (
   echo checking installation, under expected BASE
   dir /b /a "%CARGO_BASE%\bin\cargo.exe" && echo Found CARGO
   echo.
   dir /b /a  "%WABT_BASE%\bin\wasm2wat.exe" && echo Found WABT
   echo.

   echo checking in PATH
   call which cargo
   echo.
   call which wasm2wat
   exit /b
)

if NOT %var% == set (
   echo unknown action: %var%
   goto :usage
)

endlocal  & (
   if %var% == set (
      call addpath.cmd -p PATH "%CARGO_BASE%/bin"
      call addpath.cmd -p PATH  "%WABT_BASE%/bin"
      call which code
   )
)

