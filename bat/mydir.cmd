@echo off

set "prog=%~n0"

setlocal EnableDelayedExpansion

REM batch script doesn't have a $# equivalent. the following script is the best so far
set argC=0
for %%x in (%*) do Set /A argC+=1
rem echo %argC%

if NOT %argC% == 1 (
   echo ERROR:   wrong number of args. got %argC%, expected 1. args=%*
   echo usage:   %prog% pattern
   echo          %prog% list
   echo          script will append * at the end of pattern
   echo example: %prog% angular
   echo          %prog% list
   exit /b
)

set var=%1

endlocal & (
   if "%MYBASE%"=="" (
      echo ERROR:   MYBASE is not defined. run 'siteenv' first
      exit /b
   )

   if "%var%"=="list" (
      @dir "%MYBASE%/github/"
   ) else (
      @mycd "%MYBASE%/github/"%var%*
   )
)

