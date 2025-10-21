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
   echo usage:   %prog%  executable
   echo.
   echo example: %prog%  code
   exit /b
)

set var=%1

endlocal  & (
   if defined var (
      for /f "delims=" %%I in ('where %var% 2^>nul') do (
         set "fullpath=%%I"
         goto :found
      )
      echo ERROR: executable "%var%" not found in PATH
      exit /b 1

:found
      rem echo Full path: %fullpath%
        for %%F in ("%fullpath%") do (
             set "dirpath=%%~dpF"
        )
        rem echo Dir path: %dirpath%
        cd /d "%dirpath%"
    )
)
