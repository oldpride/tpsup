@echo off
@REM there are a few bash.exe in the system,
@REM C:/Windows/System32/bash.exe is for WSL
@REM C:/Program Files/Git/bin/bash.exe is Git Bash
@REM C:/cygwin64/bin/bash.exe is for Cygwin Bash

@REM example:
@REM    tpbash gitbash -c "echo hello world" # run bash build-in command
@REM    tpbash cygwin  -c "win_lastboot"     # run tpsup/scripts command
@REM    tpbash gitbash --login -i            # run gitbash in interactive mode

setlocal EnableDelayedExpansion
set "prog=%~n0"

@REM batch script doesn't have a $# equivalent. the following script is the best so far
set argC=0
for %%x in (%*) do Set /A argC+=1
@REM echo %argC%

@REM is arg is less than 1, then print usage and exit
if %argC% lss 1 (
    echo ERROR:   wrong number of args. got %argC%, expected at least 1. args=%*
    call :usage
    exit /b 1
)

@REM check whether the first arg is one of the bash types
set "bash_type=%1"
if /i "%bash_type%" neq "gitbash" (
    if /i "%bash_type%" neq "cygwin" (
        if /i "%bash_type%" neq "wsl" (
            echo ERROR:   first arg must be one of gitbash, cygwin, or wsl.
            echo          you provided "%bash_type%"
            call :usage
            exit /b 1
        )
    )
)   

@REM echo "bash_type=%bash_type%"

@REM set bash_exe to the corresponding bash executable
if /i "%bash_type%" == "gitbash" (
    set "bash_exe=C:/Program Files/Git/bin/bash.exe"
    set "PATH=C:\Program Files\Git\bin;%PATH%;%TPSUP%\scripts"
) else if /i "%bash_type%" == "cygwin" (
    set "bash_exe=C:/cygwin64/bin/bash.exe"
    set "PATH=C:\cygwin64\bin;%PATH%;%TPSUP%\scripts"
) else if /i "%bash_type%" == "wsl" (
    @REM C:\Users\tian\AppData\Local\Microsoft\WindowsApps\bash.exe is a link to below.
    set "bash_exe=C:/Windows/System32/bash.exe"
    set "PATH=C:\Windows\System32;%PATH%;%TPSUP%\scripts"
)

@REM echo using %bash_exe% to run bash command

@REM https://stackoverflow.com/questions/9363080/how-to-make-shift-work-with-in-batch-files
@REM shift the first arg in %* and save the rest in %rest_args%
  set "_args=%*"
  :: Remove %1 from %*
  set "_args=!_args:*%1 =!"
  :: The %_args% must be used here, before 'endlocal', as it is a local variable
@REM   echo /%_args%
@REM echo running: %bash_exe% %_args%
"%bash_exe%" %_args%
endlocal
exit /b 0


:: echo. is to print blank line (empty line)
:usage
   echo.
   echo usage:
   echo.
   echo    %prog% bash_type cmd [args...]
   echo.
   echo    run gitbash, cygwin bash, or wsl bash.
   echo.
   echo    C:/cygwin64/bin/bash.exe is Cygwin Bash
   echo    C:/Program Files/Git/bin/bash.exe is Gitbash
   echo    C:/Windows/System32/bash.exe is WSL bash
   echo    C:\Users\%USERNAME%\AppData\Local\Microsoft\WindowsApps\bash.exe seems 
   echo        to be a link to WSL bash.
   echo.
   echo.
   echo example:
   echo.
   echo    - run bash build-in command
   echo      %prog% gitbash -c "echo hello world"
   echo      %prog% cygwin  -c "echo hello world"
   echo      %prog% wsl     -c "echo hello world"
   echo.
   echo    - run tpsup/scripts script
   echo      %prog% gitbash "win_lastboot"
   echo      %prog% cygwin  "win_lastboot"
   echo      %prog% wsl     "lastps"
   echo.
   echo    - run gitbash in interactive mode
   echo      %prog% gitbash --login -i
   echo      %prog% cygwin  --login -i
   echo      %prog% wsl     --login -i
   echo.
   echo    - shortcut scripts
   echo    gitbash.cmd = %prog% gitbash
   echo    cygbash.cmd = %prog% cygwin
   echo    wslbash.cmd = %prog% wsl
   echo.   eg.
   echo      gitbash.cmd -c "echo hello world"
   echo      cygbash.cmd  win_lastboot
   echo      wslbash.cmd  lastps
   echo.
   echo   - run script in tpsup env
   echo     gitbash.cmd --login -c "siteenv; tradeday -1"
   echo     cygbash.cmd --login -c "siteenv; tradeday -1"
   echo     wslbash.cmd --login -c "siteenv; tradeday -1"
   echo.

   REM this is function return; it doesn't exit the script.
   REM no good way to exit script from inside a function
   exit /b 0
