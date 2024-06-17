@echo off

set "prog=%~n0"

@setlocal 

REM batch script doesn't have a $# equivalent. the following script is the best so far
set argC=0
for %%x in (%*) do Set /A argC+=1
rem echo %argC%

if NOT %argC% == 1 (
   echo ERROR:   wrong number of args. got %argC%, expected 1. args=%*
   echo usage:   %prog% path
   echo          %prog% default
   echo          'default' means search the path in PATH, not necessarily the default installation.
   echo example: %prog% c:/Users/william/chrome/Application/chrome.exe
   echo          %prog% "C:/Program Files/Google/Chrome/Application/chrome.exe"
   exit /b 1
)

set p=%1

rem how to assign cmd output to variable
rem the first % is to escape the second %
if %p% == default (
   for /f %%i in ('which.cmd chrome') do set "p2=%%i"

   if "%p2%" == "" (
      echo "chrome is not in PATH=%PATH%"
      exit /b 1
   ) else (
      echo %p2%
      p=%p2%
   )
)

rem https://stackoverflow.com/questions/29778121
call powershell -command "&{(Get-Item '%p%').VersionInfo.ProductVersion}"

@endlocal

