@echo off

set "prog=%~n0"

if "%1"=="" goto usage

set "debug_me=0"

:check_optional
   set check_again=0
   if '%1'=='-d'       (
        @echo on
        set "debug_me=1"
        set check_again=1
        goto :shift_once
    )
    if %check_again% == 0 goto :finished_optional
:shift_once
shift
goto :check_optional
:finished_optional

if "%1"=="" goto usage

set number=%1 

if exist "C:\cygwin64\bin\mintty.exe"  (
    set "cygwin_path=C:\cygwin64\bin\mintty.exe"
) 

if exist "C:\Program Files\cygwin64\bin\mintty.exe" (
    set "cygwin_path=C:\Program Files\cygwin64\bin\mintty.exe"
)

if "%cygwin_path%"=="" (
    echo cygwin not found
    exit /b 1
)

@REM unset HOME - this is to simulate a fresh cmd.exe. HOME is set by TPSUP
set "HOME_OLD=%HOME%"
set "HOME="

@REM run cygwin number of times
for /l %%x in (1, 1, %number%) do (
    "%cygwin_path%" -i /Cygwin-Terminal.ico -
)

@REM restore HOME
set "HOME=%HOME_OLD%"
exit /b 0

@REM : echo. is to print blank line (empty line)
:usage
   echo.
   echo usage:   
   echo.
   echo    %prog% [flags] number
   echo.
   echo.   launch a number of cygwin terminals
   echo.
   echo.       -d              debug flag
   echo.
   echo example:
   echo.
   echo    %prog% 8
   echo.
   @REM this is function return; it doesn't exit the script.
   @REM no good way to exit script from inside a function
   exit /b 0

