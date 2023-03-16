@echo off

set "prog=%~n0"

@REM setlocal EnableDelayedExpansion

REM batch script doesn't have a $# equivalent. the following script is the best so far
set argC=0
for %%x in (%*) do Set /A argC+=1
rem echo %argC%

if NOT %argC% == 1 (
   echo ERROR:   wrong number of args. got %argC%, expected 1. args=%*
   echo usage:   %prog% app
   echo example: %prog% angular
   exit /b
)

set var=%1

@REM there is no 'touch' equivalent in batch script.
@REM we try to copy the file to itself, 
@REM if it doesn't exist, we will be notified by error.
@REM then we create a empty file.
@REM direct the output to nul to suppress message.


copy %var% + >nul
if %errorlevel% NEQ 0 (
copy nul %var% >nul
)
