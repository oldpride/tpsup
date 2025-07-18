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
set type=%1

if "%2"=="" goto usage
set number=%2

@REM this only affects block of code inside of ()
@REM see test_if_set.cmd
setlocal ENABLEDELAYEDEXPANSION

@REM git or gitbash
if "%type%" == "gitbash" (
    set "type=git"
)
if "%type%" == "git" (
    if exist "C:\Program Files\Git\usr\bin\mintty.exe" (
        set "git_path=C:\Program Files\Git\usr\bin\mintty.exe"
    )

    if "!git_path!" == "" (
        echo git-bash not found
        exit /b 1
    )

    @REM run git-bash number of times
    for /l %%x in (1, 1, %number%) do (
        @REM use start "" to return the prompt
        start "" "!git_path!" --nodaemon -o AppID=GitForWindows.Bash -o AppLaunchCmd="C:\Program Files\Git\git-bash.exe" -o AppName="Git Bash" -i "C:\Program Files\Git\git-bash.exe" --store-taskbar-properties -- /usr/bin/bash --login -i
    )

    exit /b 0
)

@REM cyg or cygwin
if "%type%" == "cygwin" (
    set "type=cyg"
)
if "%type%" == "cyg" (
    if exist "C:\cygwin64\bin\mintty.exe"  (
        set "cygwin_path=C:\cygwin64\bin\mintty.exe"
    ) 

    if exist "C:\Program Files\cygwin64\bin\mintty.exe" (
        set "cygwin_path=C:\Program Files\cygwin64\bin\mintty.exe"
    )

    if "!cygwin_path!"=="" (
        echo cygwin not found
        exit /b 1
    )

    @REM unset HOME - this is to simulate a fresh cmd.exe. HOME is set by TPSUP
    set "HOME_OLD=%HOME%"
    set "HOME="

    @REM run cygwin number of times
    set "x=0"
    set "y=0"
    for /l %%x in (1, 1, %number%) do (
        @REM the extra - is to source .bash_profile
        @REM "!cygwin_path!" -i /Cygwin-Terminal.ico -
        @REM set offset from top-left corner 0,0, add 30 to x and y each time
        "!cygwin_path!" -i /Cygwin-Terminal.ico -p !x!,!y! -
        set /a "x+=30"
        set /a "y+=30"

        @REM sleep in between to avoid launching too many terminals at once
        timeout /t 2 /nobreak >nul
    )

    @REM restore HOME
    set "HOME=%HOME_OLD%"
    exit /b 0
)

@REM cmd or bat or batch
if "%type%" == "bat" (
    set "type=cmd"
)
if "%type%" == "batch" (
    set "type=cmd"
)
if "%type%" == "cmd" (
    @REM run cmd.exe number of times
    for /l %%x in (1, 1, %number%) do (
        start "" cmd.exe
    )

    exit /b 0
)

endlocal

@REM : echo. is to print blank line (empty line)
:usage
   echo.
   echo usage:   
   echo.
   echo    %prog% [flags] "cyg|git|cmd" number
   echo.
   echo.   launch a number of cygwin terminals
   echo.       'cyg' is the cygwin terminals. same as 'cygwin'.
   echo.       'git' is the git-bash terminals. same as 'gitbash'.
   echo.       'cmd' is the cmd.exe terminals. same as 'bat' or 'batch'.
   echo.
   echo.       -d              debug flag
   echo.
   echo example:
   echo.
   echo    %prog% cyg 2
   echo.   %prog% git 3
   echo.   %prog% cmd 3
   echo.
   @REM this is function return; it doesn't exit the script.
   @REM no good way to exit script from inside a function
   exit /b 0
